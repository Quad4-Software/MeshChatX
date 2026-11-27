# SPDX-License-Identifier: 0BSD

"""Property tests for websocket runtime state machines.

Covers apply_subscribe/client_allows_topic subscription algebra, TokenBucket
bounds under arbitrary consume sequences, BroadcastSeqState gap_hint closed
outcomes, topic_for_type totality, and CoalesceBuffer latest-wins merging.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.websocket_runtime import (
    COALESCE_TYPES,
    WS_ALL_TOPICS,
    WS_RATE_BURST,
    WS_RATE_RATE,
    BroadcastSeqState,
    CoalesceBuffer,
    TokenBucket,
    apply_subscribe,
    client_allows_topic,
    default_subscriptions,
    message_rate_cost,
    topic_for_type,
)

TOPICS = sorted(WS_ALL_TOPICS)


def _client():
    # SimpleNamespace supports arbitrary attribute writes like the aiohttp
    # websocket wrapper the runtime annotates.
    return SimpleNamespace()


def _topic_lists():
    return st.lists(
        st.one_of(
            st.sampled_from(TOPICS),
            st.text(max_size=24),
            st.integers(),
            st.none(),
        ),
        max_size=12,
    )


def _ops():
    return st.lists(
        st.tuples(st.booleans(), _topic_lists()),
        min_size=1,
        max_size=40,
    )


def _model_subscriptions(ops):
    current = set(default_subscriptions())
    for subscribe, topics in ops:
        if not isinstance(topics, list):
            continue
        for raw in topics:
            if not isinstance(raw, str):
                continue
            name = raw.strip()
            if name not in WS_ALL_TOPICS:
                continue
            if subscribe:
                current.add(name)
            else:
                current.discard(name)
    return current


@given(ops=_ops())
@settings(max_examples=150, deadline=None)
def test_apply_subscribe_matches_set_model(ops):
    client = _client()
    for subscribe, topics in ops:
        apply_subscribe(client, topics, subscribe=subscribe)
    expected = _model_subscriptions(ops)
    actual = client._meshchatx_ws_topics
    assert actual == expected


@given(ops=_ops())
@settings(max_examples=150, deadline=None)
def test_client_allows_topic_agrees_with_subscriptions(ops):
    client = _client()
    for subscribe, topics in ops:
        apply_subscribe(client, topics, subscribe=subscribe)
    subs = client._meshchatx_ws_topics
    for topic in TOPICS:
        assert client_allows_topic(client, topic) == (topic in subs)


@given(ops=_ops())
@settings(max_examples=150, deadline=None)
def test_changed_entries_are_real_flips_without_duplicates(ops):
    client = _client()
    for subscribe, topics in ops:
        current = getattr(client, "_meshchatx_ws_topics", None)
        before = set(current if current is not None else default_subscriptions())
        changed = apply_subscribe(client, topics, subscribe=subscribe)
        after = set(client._meshchatx_ws_topics)
        # No duplicates in the change report.
        assert len(changed) == len(set(changed))
        for name in changed:
            flipped = (name in before) != (name in after)
            assert flipped, f"{name} reported changed but membership is unchanged"
            # The direction of the flip matches the operation.
            if subscribe:
                assert name in after and name not in before
            else:
                assert name not in after and name in before


@given(
    data=st.one_of(
        st.none(),
        st.integers(),
        st.text(max_size=30),
        st.dictionaries(st.text(max_size=4), st.integers(), max_size=3),
    )
)
@settings(max_examples=100, deadline=None)
def test_non_list_topics_never_mutate(data):
    client = _client()
    apply_subscribe(client, data, subscribe=True)
    apply_subscribe(client, data, subscribe=False)
    # A non-list payload must not even initialise the subscription attribute.
    assert getattr(client, "_meshchatx_ws_topics", None) is None
    assert apply_subscribe(client, data, subscribe=True) == []


# --- TokenBucket -------------------------------------------------------------


def _consume_with_elapsed(bucket, elapsed, cost):
    # Rewind the bucket clock so consume() observes `elapsed` seconds of
    # refill without sleeping in wall time.
    bucket.updated = time.monotonic() - elapsed
    return bucket.consume(cost)


@given(
    ops=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
            st.floats(min_value=0.0, max_value=20.0, allow_nan=False),
        ),
        min_size=1,
        max_size=60,
    ),
)
@settings(max_examples=150, deadline=None)
def test_token_bucket_stays_within_bounds(ops):
    bucket = TokenBucket(rate=WS_RATE_RATE, burst=WS_RATE_BURST)
    for elapsed, cost in ops:
        _consume_with_elapsed(bucket, elapsed, cost)
        assert 0.0 <= bucket.tokens <= bucket.burst + 1e-9


@given(
    elapsed=st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
    cost=st.floats(min_value=0.01, max_value=20.0, allow_nan=False),
)
@settings(max_examples=150, deadline=None)
def test_token_bucket_acceptance_matches_available_tokens(elapsed, cost):
    rate, burst = 10.0, 25.0
    bucket = TokenBucket(rate=rate, burst=burst)
    # Drain some tokens first so the refill math matters.
    bucket.consume(burst / 2)
    pre_tokens = min(burst, bucket.tokens + elapsed * rate)
    result = _consume_with_elapsed(bucket, elapsed, cost)
    if pre_tokens >= cost:
        assert result is True
    else:
        assert result is False


@given(wait=st.floats(min_value=6.5, max_value=60.0, allow_nan=False))
@settings(max_examples=80, deadline=None)
def test_idle_bucket_always_allows_full_burst(wait):
    # rate 10/s means 6 s refills a 60 burst; anything longer must saturate.
    bucket = TokenBucket(rate=10.0, burst=60.0)
    bucket.consume(60.0)
    assert bucket.tokens < 1.0
    assert _consume_with_elapsed(bucket, wait, 60.0) is True


# --- BroadcastSeqState -------------------------------------------------------


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def seq_state():
    return BroadcastSeqState()


def test_seq_stamps_are_strictly_increasing(seq_state):
    async def scenario():
        stamps = []
        for i in range(20):
            n = await seq_state.stamp({"type": "announce", "i": i})
            stamps.append(n)
        return stamps

    stamps = asyncio.run(scenario())
    assert stamps == sorted(stamps)
    assert len(set(stamps)) == len(stamps)
    assert stamps[-1] == seq_state.seq


@given(
    n_stamps=st.integers(min_value=0, max_value=40),
    since=st.integers(min_value=0, max_value=50),
)
@settings(max_examples=150, deadline=None)
def test_gap_hint_closed_outcomes(n_stamps, since):
    state = BroadcastSeqState()

    async def scenario():
        for i in range(n_stamps):
            await state.stamp({"type": "announce", "i": i})
        return state.gap_hint(since)

    hint = asyncio.run(scenario())
    assert hint["since_seq"] == since
    assert hint["current_seq"] == n_stamps
    if since > n_stamps:
        # A cursor ahead of the server is stale: always a resync gap.
        assert hint["status"] == "gap"
        assert hint["resync"] is True
        assert hint["buffered"] == 0
    elif since == n_stamps:
        assert hint["status"] == "ok"
    else:
        assert hint["status"] == "gap"
        assert hint["resync"] is True
        assert 0 < hint["buffered"] <= min(256, n_stamps - since)


# --- topic_for_type totality -------------------------------------------------


@given(
    msg_type=st.one_of(
        st.none(), st.text(max_size=60), st.integers(), st.sampled_from(TOPICS)
    )
)
@settings(max_examples=150, deadline=None)
def test_topic_for_type_is_total_and_closed(msg_type):
    topic = topic_for_type(
        msg_type if isinstance(msg_type, str) or msg_type is None else str(msg_type)
    )
    assert topic in WS_ALL_TOPICS or topic == "other"
    assert isinstance(topic, str) and topic


@given(
    msg_type=st.sampled_from(
        sorted(
            {
                "nomadnet.page.download",
                "rns.link.request",
                "lxm.ingest_uri",
                "ping",
                "other",
            }
        )
    )
)
@settings(max_examples=50, deadline=None)
def test_message_rate_cost_is_positive(msg_type):
    cost = message_rate_cost(msg_type)
    assert cost >= 1.0


# --- CoalesceBuffer ----------------------------------------------------------


def _coalesce_ops():
    return st.lists(
        st.tuples(
            st.sampled_from(sorted(COALESCE_TYPES | {"config", "lxmf.delivery"})),
            st.text(alphabet="abcdef", min_size=1, max_size=6),
            st.integers(min_value=0, max_value=5),
        ),
        min_size=1,
        max_size=50,
    )


@given(ops=_coalesce_ops())
@settings(max_examples=100, deadline=None)
def test_coalesce_only_accepts_known_types_and_latest_wins(ops):
    flushed: list[dict] = []

    async def flush_cb(payload):
        flushed.append(payload)

    async def scenario():
        buf = CoalesceBuffer(flush_cb, window_sec=0.01)
        accepted = {}
        for mtype, ident, seq in ops:
            payload = {"type": mtype, "destination_hash": ident, "seq": seq}
            ok = buf.offer(payload)
            if mtype in COALESCE_TYPES:
                assert ok is True
                accepted[(mtype, ident)] = seq
            else:
                assert ok is False
        await buf.flush_now()
        return accepted

    accepted = asyncio.run(scenario())
    # Every flushed payload must be the latest offer for its key: no stale
    # value may survive the merge.
    seen = {}
    for payload in flushed:
        key = (payload["type"], payload["destination_hash"])
        assert key not in seen, "duplicate flush for one key within a single flush"
        seen[key] = payload["seq"]
    for key, seq in seen.items():
        assert accepted[key] == seq
