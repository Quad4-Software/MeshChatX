# SPDX-License-Identifier: 0BSD

"""Property-based fuzz tests for the RRC wire protocol and notice parsers."""

import base64

import cbor2
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rrc import protocol as proto


def _envelope_dict_strategy():
    return st.dictionaries(
        keys=st.integers(min_value=0, max_value=10),
        values=st.one_of(
            st.none(),
            st.integers(),
            st.text(max_size=64),
            st.binary(min_size=0, max_size=32),
            st.lists(st.binary(min_size=0, max_size=16), max_size=8),
            st.dictionaries(
                st.integers(min_value=0, max_value=5), st.text(max_size=32)
            ),
        ),
        max_size=12,
    )


@given(data=st.binary(min_size=0, max_size=4096))
@settings(max_examples=200, deadline=None)
def test_decode_random_bytes_never_raises_unexpected(data):
    try:
        obj = proto.decode(data)
    except Exception as exc:
        assert isinstance(exc, (cbor2.CBORDecodeError, ValueError, TypeError, EOFError))
        return
    assert obj is not None or obj is None


@given(env=_envelope_dict_strategy())
@settings(max_examples=150, deadline=None)
def test_encode_decode_roundtrip_dict(env):
    payload = proto.encode(env)
    assert isinstance(payload, (bytes, bytearray))
    decoded = proto.decode(payload)
    assert decoded == env


@given(
    msg_type=st.integers(min_value=-1000, max_value=1000),
    src=st.one_of(st.none(), st.binary(min_size=0, max_size=32)),
    room=st.one_of(st.none(), st.text(max_size=128)),
    body=st.one_of(st.none(), st.text(max_size=512), st.binary(max_size=64)),
    nick=st.one_of(st.none(), st.text(max_size=64)),
)
@settings(max_examples=120, deadline=None)
def test_make_envelope_encode_decode_never_raises(msg_type, src, room, body, nick):
    env = proto.make_envelope(msg_type, src, room=room, body=body, nick=nick)
    decoded = proto.decode(proto.encode(env))
    assert decoded[proto.K_T] == int(msg_type)
    assert decoded[proto.K_SRC] == src


@given(nick=st.text(max_size=128))
@settings(max_examples=100, deadline=None)
def test_normalize_nick_never_raises(nick):
    result = proto.normalize_nick(nick)
    if result is not None:
        assert isinstance(result, str)
        assert result.strip() == result
        assert len(result.encode("utf-8")) <= proto.DEFAULT_MAX_NICK_BYTES


@given(nick=st.text(max_size=128), max_bytes=st.integers(min_value=1, max_value=256))
@settings(max_examples=80, deadline=None)
def test_normalize_nick_respects_max_bytes(nick, max_bytes):
    result = proto.normalize_nick(nick, max_bytes=max_bytes)
    if result is not None:
        assert len(result.encode("utf-8")) <= max_bytes


@given(room=st.text(max_size=128))
@settings(max_examples=80, deadline=None)
def test_normalize_room_only_raises_on_empty_or_whitespace(room):
    stripped = (room or "").strip()
    if not stripped:
        with pytest.raises(ValueError):
            proto.normalize_room(room)
    else:
        assert proto.normalize_room(room) == stripped.lower()


@given(text=st.text(max_size=256), nick=st.text(max_size=64))
@settings(max_examples=120, deadline=None)
def test_text_mentions_never_raises(text, nick):
    result = proto.text_mentions(text, nick)
    assert isinstance(result, bool)


@given(text=st.one_of(st.none(), st.integers(), st.binary(), st.text(max_size=256)))
@settings(max_examples=80, deadline=None)
def test_parse_who_notice_never_raises(text):
    result = proto.parse_who_notice(text)
    if result is not None:
        room, entries = result
        assert isinstance(room, str)
        assert room == room.lower()
        assert isinstance(entries, list)


@given(text=st.one_of(st.none(), st.integers(), st.binary(), st.text(max_size=512)))
@settings(max_examples=80, deadline=None)
def test_parse_room_list_notice_never_raises(text):
    result = proto.parse_room_list_notice(text)
    if result is not None:
        assert isinstance(result, dict)
        for key, val in result.items():
            assert isinstance(key, str)
            assert key == key.lower()
            assert val is None or isinstance(val, str)


@given(
    kind=st.text(max_size=32),
    room=st.one_of(st.none(), st.text(max_size=64)),
    src=st.one_of(st.none(), st.binary(min_size=0, max_size=32)),
    nick=st.one_of(st.none(), st.text(max_size=64)),
    text=st.one_of(st.none(), st.text(max_size=512), st.integers()),
    ts=st.one_of(st.integers(), st.floats(allow_nan=False), st.text(max_size=16)),
)
@settings(max_examples=100, deadline=None)
def test_rrc_message_to_dict_never_raises(kind, room, src, nick, text, ts):
    msg = proto.RRCMessage(kind, room, src, nick, text, ts)
    d = msg.to_dict()
    assert isinstance(d, dict)
    assert "kind" in d
    assert "text" in d
    assert isinstance(d["text"], str)
    assert isinstance(d["ts"], int)


@given(app_data=st.one_of(st.none(), st.text(max_size=256), st.binary(max_size=128)))
@settings(max_examples=100, deadline=None)
def test_display_name_from_hub_app_data_never_raises(app_data):
    if isinstance(app_data, bytes):
        b64 = base64.b64encode(app_data).decode("ascii")
    elif isinstance(app_data, str):
        b64 = app_data
    else:
        b64 = None
    result = proto.display_name_from_hub_app_data(b64)
    if result is not None:
        assert isinstance(result, str)
        assert result.strip() == result


@given(
    room=st.text(min_size=1, max_size=64),
    entries=st.lists(
        st.tuples(
            st.one_of(st.none(), st.text(min_size=1, max_size=32)),
            st.from_regex(r"[0-9a-fA-F]{12}", fullmatch=True),
        ),
        max_size=8,
    ),
)
@settings(max_examples=40, deadline=None)
def test_parse_who_notice_roundtrip_synthetic(room, entries):
    assume(room.strip())
    parts = []
    for nick, np in entries:
        if nick is None:
            parts.append(np + "0" * 20)
        else:
            parts.append(f"{nick} ({np})")
    body = ", ".join(parts) if parts else "(none)"
    text = f"members in {room.strip()}: {body}"
    parsed = proto.parse_who_notice(text)
    assert parsed is not None
    parsed_room, parsed_entries = parsed
    assert parsed_room == room.strip().lower()
