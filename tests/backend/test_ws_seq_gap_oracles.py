# SPDX-License-Identifier: 0BSD

"""Oracle tests for BroadcastSeqState.gap_hint."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.websocket_runtime import BroadcastSeqState


def oracle_gap_hint(seq: int, since_seq: int) -> dict:
    # Only an exact match means the client is caught up. A cursor ahead of
    # the server is stale state from before a restart and must resync.
    if since_seq == seq:
        return {"status": "ok", "since_seq": since_seq, "current_seq": seq}
    return {
        "status": "gap",
        "since_seq": since_seq,
        "current_seq": seq,
        "resync": True,
    }


@pytest.mark.asyncio
async def test_gap_hint_ok_when_caught_up():
    state = BroadcastSeqState()
    payload = {"type": "announce"}
    n = await state.stamp(payload)
    hint = state.gap_hint(n)
    assert hint["status"] == "ok"
    assert hint.get("resync") is not True
    assert hint["current_seq"] == n


@pytest.mark.asyncio
async def test_gap_hint_resync_when_client_ahead_after_restart():
    """Client cursor ahead of server seq must resync.

    A cursor larger than the server seq is stale state from a previous
    server epoch (restart resets seq to zero); the client must resync.
    """
    state = BroadcastSeqState()
    await state.stamp({"type": "announce"})
    hint = state.gap_hint(999)
    assert hint["status"] == "gap"
    assert hint["resync"] is True
    assert hint["current_seq"] == 1


@pytest.mark.asyncio
async def test_gap_hint_resync_when_behind_even_if_ring_empty():
    state = BroadcastSeqState()
    # Force seq ahead without filling meaningful ring entries for old seqs
    for i in range(5):
        await state.stamp({"type": f"t{i}"})
    hint = state.gap_hint(0)
    assert hint["status"] == "gap"
    assert hint["resync"] is True
    assert hint["current_seq"] == 5


@given(
    stamps=st.integers(min_value=0, max_value=40),
    since=st.integers(min_value=0, max_value=50),
)
@settings(max_examples=80, deadline=None)
def test_gap_hint_matches_pure_oracle(stamps, since):
    import asyncio

    async def run():
        state = BroadcastSeqState()
        for i in range(stamps):
            await state.stamp({"type": "x", "i": i})
        expected = oracle_gap_hint(state.seq, since)
        actual = state.gap_hint(since)
        assert actual["status"] == expected["status"]
        assert actual["current_seq"] == expected["current_seq"]
        assert actual.get("resync") == expected.get("resync")

    asyncio.run(run())
