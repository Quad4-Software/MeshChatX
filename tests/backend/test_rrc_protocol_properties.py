# SPDX-License-Identifier: 0BSD
"""Property-based tests for RRC protocol codecs and parsers.

Randomized roundtrips pin the encode/decode contract; the fuzz parsers
must never crash or produce out-of-contract results on adversarial
input, matching the malformed-input hardening fixes.
"""

import re

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rrc import protocol as proto

_NAME_CHARS = st.characters(
    whitelist_categories=("L", "N", "P", "S", "Zs"), max_codepoint=0x2FFF
)
_TEXT = st.text(_NAME_CHARS, max_size=400)
_ROOM = st.text(_NAME_CHARS, min_size=1, max_size=80)
_HEX16 = st.binary(min_size=16, max_size=16)


@given(
    t=st.integers(min_value=0, max_value=255),
    src=_HEX16,
    room=st.one_of(st.none(), _ROOM),
    body=st.one_of(st.none(), _TEXT),
    nick=st.one_of(st.none(), _TEXT),
    mid=st.one_of(st.none(), st.binary(max_size=32)),
    ts=st.one_of(st.none(), st.integers(min_value=0, max_value=2**63 - 1)),
)
@settings(max_examples=200, deadline=None)
def test_envelope_roundtrip(t, src, room, body, nick, mid, ts):
    env = proto.make_envelope(t, src, room=room, body=body, nick=nick, mid=mid, ts=ts)
    decoded = proto.decode(proto.encode(env))
    assert decoded == env


@given(data=st.binary(max_size=4096))
@settings(max_examples=300, deadline=None)
def test_decode_never_crashes(data):
    """Arbitrary wire bytes: decode may raise a normal codec error only."""
    try:
        proto.decode(data)
    except Exception as exc:
        name = type(exc).__name__
        assert name.startswith("CBOR") or name in {
            "ValueError",
            "EOFError",
            "OverflowError",
            "UnicodeDecodeError",
            "TypeError",
        }, f"unexpected exception {name}: {exc}"


@given(room=_TEXT)
@settings(max_examples=200, deadline=None)
def test_normalize_room_bounds(room):
    try:
        out = proto.normalize_room(room)
    except ValueError:
        return
    assert out == out.lower().strip()
    assert out


@given(nick=st.one_of(st.none(), _TEXT), maxb=st.integers(1, 200))
@settings(max_examples=150, deadline=None)
def test_normalize_nick_byte_bound(nick, maxb):
    out = proto.normalize_nick(nick, max_bytes=maxb)
    if out is None:
        return
    assert len(out.encode("utf-8")) <= maxb


@given(text=_TEXT, nick=_TEXT)
@settings(max_examples=200, deadline=None)
def test_text_mentions_no_crash(text, nick):
    out = proto.text_mentions(text, nick)
    assert isinstance(out, bool)
    if nick and nick in text:
        # A literal substring may still not count (word boundaries), but a
        # returned True requires a real regex match path, not an error.
        pat = proto.mention_re(nick)
        if pat is not None:
            assert pat.search(text) or not out


@given(text=_TEXT)
@settings(max_examples=200, deadline=None)
def test_room_list_notice_never_crashes(text):
    out = proto.parse_room_list_notice_details(text)
    assert out is None or isinstance(out, dict)
    if isinstance(out, dict):
        for name, info in out.items():
            assert isinstance(name, str)
            assert set(info) == {"topic", "has_key"}
            assert info["topic"] is None or isinstance(info["topic"], str)
            assert isinstance(info["has_key"], bool)


@given(text=_TEXT)
@settings(max_examples=200, deadline=None)
def test_who_notice_never_crashes(text):
    out = proto.parse_who_notice(text)
    assert out is None or isinstance(out, list)


@given(
    body=_TEXT,
    nick=st.text(
        st.characters(whitelist_categories=("L", "N"), max_codepoint=0x7A),
        min_size=1,
        max_size=24,
    ),
)
@settings(
    max_examples=150,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow,),
)
def test_mention_regex_is_bounded_and_safe(body, nick):
    """Adversarial nicks must not blow up regex compilation or matching."""
    pat = proto.mention_re(nick)
    if pat is None:
        return
    assert isinstance(pat, re.Pattern)
    # Search must terminate quickly even on pathological inputs.
    pat.search(body)


@given(events=st.lists(st.integers(min_value=0, max_value=3), min_size=1, max_size=12))
@settings(
    max_examples=80,
    deadline=None,
    # Each example builds a fresh manager and never loads prior history,
    # so the shared tmp_path cannot leak state between generated inputs.
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
def test_replay_count_matches_delivery_totals(tmp_path, events):
    """Randomized deliveries: rows equal distinct messages, counts equal copies.

    Each event either introduces a new message or replays an earlier one
    with its original envelope id. Whatever the order, one row per distinct
    message must remain and its repeat count must match the number of
    deliveries the client saw.
    """
    from tests.backend.test_rrc_protocol import make_manager

    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("lobby")
    mids = {}
    expected = {}
    for i in events:
        body = "m" + str(i)
        mid = mids.get(i)
        env = proto.make_envelope(
            proto.T_MSG,
            src=b"\x30" * 16,
            room="lobby",
            nick="dave",
            body=body,
            mid=mid,
        )
        mids[i] = env[proto.K_ID]
        hub._handle_msg(env)
        expected[body] = expected.get(body, 0) + 1

    rows = hub.get_messages("lobby")
    assert len(rows) == len(expected)
    assert {m.text: m.dup_count for m in rows} == expected
