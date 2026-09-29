"""Tests for RRC CBOR encoding and client session behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cbor2
import pytest
import RNS
from hypothesis import given, settings
from hypothesis import strategies as st

from lxmfy import BotConfig, LXMFBot
from lxmfy.rrc import (
    DEFAULT_DEST_NAME,
    RRCClient,
    RRCManager,
    RRC_VERSION,
    STATUS_CONNECTED,
    T_ACTION,
    T_ERROR,
    T_HELLO,
    T_JOINED,
    T_MSG,
    T_NOTICE,
    T_PING,
    T_PONG,
    T_WELCOME,
    decode_envelope,
    encode_envelope,
    make_envelope,
    normalize_room,
)
from lxmfy.rrc.constants import (
    B_HELLO_CAPS,
    B_HELLO_NAME,
    B_HELLO_VER,
    B_WELCOME_HUB,
    B_WELCOME_LIMITS,
    B_WELCOME_VER,
    CAP_ACTION,
    K_BODY,
    K_ID,
    K_NICK,
    K_ROOM,
    K_SRC,
    K_T,
    K_TS,
    K_V,
    L_MAX_MSG_BODY_BYTES,
    L_MAX_NICK_BYTES,
)


def _src() -> bytes:
    return bytes(range(16))


def test_normalize_room():
    assert normalize_room(" Lobby ") == "lobby"
    assert normalize_room("#General") == "#general"
    with pytest.raises(ValueError):
        normalize_room("   ")
    with pytest.raises(ValueError):
        normalize_room(None)


def test_make_envelope_roundtrip_cbor():
    src = _src()
    env = make_envelope(
        T_MSG,
        src=src,
        room="lobby",
        body="Hello, world!",
        nick="alice",
        mid=b"\x7a\x3f\x8e\x12\x45\xc9\xa1\x6d",
        ts=1737849600000,
    )
    raw = encode_envelope(env)
    decoded = decode_envelope(raw)
    assert decoded is not None
    assert decoded[K_V] == RRC_VERSION
    assert decoded[K_T] == T_MSG
    assert decoded[K_SRC] == src
    assert decoded[K_ROOM] == "lobby"
    assert decoded[K_BODY] == "Hello, world!"
    assert decoded[K_NICK] == "alice"
    assert decoded[K_ID] == b"\x7a\x3f\x8e\x12\x45\xc9\xa1\x6d"
    assert decoded[K_TS] == 1737849600000


def test_envelope_rejects_bad_src():
    with pytest.raises(ValueError):
        make_envelope(T_HELLO, src=b"short")


def test_decode_malformed_returns_none():
    assert decode_envelope(b"not-cbor") is None
    assert decode_envelope(cbor2.dumps(["list"])) is None


def test_unknown_keys_preserved():
    src = _src()
    env = make_envelope(T_MSG, src=src, room="x", body="y")
    env[99] = "extension"
    decoded = decode_envelope(encode_envelope(env))
    assert decoded is not None
    assert decoded[99] == "extension"


def test_spec_size_budget_example():
    """Worst-case MSG budget from 3-RRC should stay near the MTU."""
    import os

    src = _src()
    env = make_envelope(
        T_MSG,
        src=src,
        room="a" * 64,
        body="b" * 350,
        nick="c" * 32,
        mid=os.urandom(8),
        ts=(1 << 40),
    )
    encoded = encode_envelope(env)
    assert len(encoded) <= 500


@given(
    room=st.text(min_size=1, max_size=32).filter(lambda s: s.strip()),
    body=st.text(min_size=1, max_size=120),
    nick=st.one_of(st.none(), st.text(min_size=1, max_size=16)),
)
@settings(max_examples=40, deadline=None)
def test_envelope_roundtrip_property(room, body, nick):
    src = _src()
    env = make_envelope(T_MSG, src=src, room=room, body=body, nick=nick)
    decoded = decode_envelope(encode_envelope(env))
    assert decoded is not None
    assert decoded[K_T] == T_MSG
    assert decoded[K_BODY] == body
    assert decoded[K_ROOM] == room
    if nick:
        assert decoded[K_NICK] == nick
    else:
        assert K_NICK not in decoded


def _client(events: list | None = None) -> RRCClient:
    identity = MagicMock()
    identity.hash = _src()
    hub = bytes(range(16, 32))

    def on_event(event, client, payload):
        if events is not None:
            events.append((event, payload))

    return RRCClient(
        identity=identity,
        hub_hash=hub,
        nick="TestBot",
        auto_reconnect=False,
        on_event=on_event,
    )


def test_client_handles_welcome_and_limits():
    events = []
    client = _client(events)
    body = {
        B_WELCOME_HUB: "ExampleHub",
        B_WELCOME_VER: "0.1.0",
        B_WELCOME_LIMITS: {
            L_MAX_NICK_BYTES: 24,
            L_MAX_MSG_BODY_BYTES: 200,
        },
    }
    env = make_envelope(T_WELCOME, src=bytes(range(16, 32)), body=body)
    client._on_packet(encode_envelope(env))
    assert client.welcomed is True
    assert client.status == STATUS_CONNECTED
    assert client.hub_name == "ExampleHub"
    assert client.max_nick_bytes == 24
    assert client.max_msg_body_bytes == 200
    assert any(e[0] == "welcome" for e in events)


def test_client_handles_msg_and_mention():
    events = []
    client = _client(events)
    peer = bytes(range(32, 48))
    env = make_envelope(
        T_MSG,
        src=peer,
        room="Lobby",
        body="hey @TestBot are you there?",
        nick="alice",
    )
    client._on_packet(encode_envelope(env))
    msgs = [p for e, p in events if e == "msg"]
    assert len(msgs) == 1
    assert msgs[0].room == "lobby"
    assert msgs[0].mention is True
    assert msgs[0].nick == "alice"
    assert client.nicks[peer] == "alice"


def test_client_handles_notice_and_action():
    events = []
    client = _client(events)
    peer = bytes(range(32, 48))
    notice = make_envelope(T_NOTICE, src=peer, room="lobby", body="system note")
    action = make_envelope(T_ACTION, src=peer, room="lobby", body="waves")
    client._on_packet(encode_envelope(notice))
    client._on_packet(encode_envelope(action))
    kinds = [e for e, _ in events]
    assert "notice" in kinds
    assert "action" in kinds


def test_client_ping_pong():
    events = []
    client = _client(events)
    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE

    with patch.object(client, "_send_env") as send_env:
        ping = make_envelope(T_PING, src=bytes(range(16, 32)), body=b"12345678")
        client._on_packet(encode_envelope(ping))
        assert send_env.called
        pong_env = send_env.call_args[0][0]
        assert pong_env[K_T] == T_PONG
        assert pong_env[K_BODY] == b"12345678"

    body = b"abcdefgh"
    client._pending_pings[body] = 1
    pong = make_envelope(T_PONG, src=bytes(range(16, 32)), body=body)
    client._on_packet(encode_envelope(pong))
    assert any(e[0] == "pong" for e in events)


def test_client_joined_and_error():
    events = []
    client = _client(events)
    client._pending_joins.add("lobby")
    joined = make_envelope(
        T_JOINED,
        src=bytes(range(16, 32)),
        room="lobby",
        body=[_src()],
    )
    client._on_packet(encode_envelope(joined))
    assert "lobby" in client.rooms
    assert any(e[0] == "joined" for e in events)

    client._pending_joins.add("secret")
    err = make_envelope(
        T_ERROR,
        src=bytes(range(16, 32)),
        room="secret",
        body="denied",
    )
    client._on_packet(encode_envelope(err))
    assert "secret" not in client.rooms
    assert any(e[0] == "error" for e in events)


def test_client_send_message_requires_active_link():
    client = _client()
    with pytest.raises(RuntimeError):
        client.send_message("lobby", "hi")


def test_client_send_message_encodes_and_tracks_id():
    client = _client()
    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE
    client.welcomed = True
    with (
        patch.object(client, "_packet_would_fit", return_value=True),
        patch("lxmfy.rrc.client.RNS.Packet") as packet_cls,
    ):
        packet = MagicMock()
        packet_cls.return_value = packet
        mid = client.send_message("Lobby", "hello there")
        assert isinstance(mid, bytes)
        assert mid in client._sent_ids
        packet.send.assert_called_once()
        payload = packet_cls.call_args[0][1]
        decoded = decode_envelope(payload)
        assert decoded is not None
        assert decoded[K_T] == T_MSG
        assert decoded[K_ROOM] == "lobby"
        assert decoded[K_BODY] == "hello there"


def test_hello_body_shape():
    client = _client()
    link = MagicMock()
    with patch("lxmfy.rrc.client.RNS.Packet") as packet_cls:
        packet = MagicMock()
        packet_cls.return_value = packet
        client._send_hello(link)
        payload = packet_cls.call_args[0][1]
        env = decode_envelope(payload)
        assert env is not None
        assert env[K_T] == T_HELLO
        assert env[K_BODY][B_HELLO_NAME] == "lxmfy"
        assert env[K_BODY][B_HELLO_VER]
        assert env[K_BODY][B_HELLO_CAPS][CAP_ACTION] is True


def test_manager_connect_and_status():
    identity = MagicMock()
    identity.hash = _src()
    manager = RRCManager(identity=identity, nick="MgrBot", auto_reconnect=False)
    hub = bytes(range(16, 32)).hex()

    with patch.object(RRCClient, "connect") as connect:
        client = manager.connect(hub, rooms=["lobby"])
        connect.assert_called_once()
        assert client.nick == "MgrBot"
        assert "lobby" in client._auto_join_rooms
        assert manager.get(hub) is client
        assert len(manager.status()) == 1

    manager.disconnect(hub)
    assert manager.get(hub) is None


def test_bot_exposes_rrc_in_test_mode(tmp_path):
    config = BotConfig(
        test_mode=True,
        config_path=str(tmp_path / "cfg"),
        storage_path=str(tmp_path / "data"),
        announce_enabled=False,
        cogs_enabled=False,
        landlock_enabled=False,
        rrc_enabled=True,
        rrc_hubs=["aabbccddeeff00112233445566778899"],
        rrc_rooms=["lobby"],
        rrc_nick="UnitBot",
    )
    bot = LXMFBot(**config.__dict__)
    assert isinstance(bot.rrc, RRCManager)
    assert bot.rrc.nick == "UnitBot"
    assert bot.rrc.dest_name == DEFAULT_DEST_NAME

    called = []

    @bot.on_rrc
    def handler(event, client, payload):
        called.append(event)

    bot._rrc_event("welcome", MagicMock(hub_hash=_src()), {"hub_name": "x"})
    assert called == ["welcome"]

    with pytest.raises(RuntimeError):
        bot.connect_rrc("aabbccddeeff00112233445566778899")


def test_default_dest_name_constant():
    assert DEFAULT_DEST_NAME == "rrc.hub"
    assert RRC_VERSION == 1


def test_validate_envelope_rejects_bad_fields():
    from lxmfy.rrc import validate_envelope

    src = _src()
    good = make_envelope(T_MSG, src=src, room="lobby", body="hi")
    assert validate_envelope(good) is True

    bad_version = dict(good)
    bad_version[K_V] = 99
    assert validate_envelope(bad_version) is False

    bad_src = dict(good)
    bad_src[K_SRC] = b"short"
    assert validate_envelope(bad_src) is False

    bad_id = dict(good)
    bad_id[K_ID] = b"1234"
    assert validate_envelope(bad_id) is False


def test_pre_welcome_send_rejected():
    client = _client()
    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE
    client.welcomed = False
    with pytest.raises(RuntimeError, match="not welcomed"):
        client.send_message("lobby", "too early")


def test_on_closed_clears_session_and_preserves_rejoin():
    client = _client()
    client.auto_reconnect = False
    client.rooms.add("lobby")
    client.nicks[_src()] = "alice"
    client._pending_pings[b"12345678"] = 1
    client.welcomed = True
    client._on_closed(MagicMock())
    assert client.rooms == set()
    assert client.nicks == {}
    assert client._pending_pings == {}
    assert client.welcomed is False
    assert "lobby" in client._rejoin_rooms


def test_welcome_rejoins_previous_rooms():
    client = _client()
    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE
    client._rejoin_rooms.add("lobby")
    client._auto_join_rooms = ["ops"]
    with patch.object(client, "join") as join:
        env = make_envelope(
            T_WELCOME,
            src=bytes(range(16, 32)),
            body={B_WELCOME_HUB: "Hub"},
        )
        client._on_packet(encode_envelope(env))
        joined = {call.args[0] for call in join.call_args_list}
        assert joined == {"lobby", "ops"}
    assert client.connected is True


def test_hub_limit_enforcement():
    client = _client()
    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE
    client.welcomed = True
    client.max_msg_body_bytes = 5
    with pytest.raises(ValueError, match="too long"):
        client.send_message("lobby", "toolong")

    client.max_room_name_bytes = 3
    with pytest.raises(ValueError, match="room name too long"):
        client.join("lobby")

    client.max_room_name_bytes = 64
    client.max_rooms_per_session = 1
    client.rooms.add("a")
    with pytest.raises(RuntimeError, match="max rooms"):
        client.join("b")

    with pytest.raises(ValueError, match="nick too long"):
        client.set_nick("x" * 100)


def test_rate_limit_enforcement():
    client = _client()
    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE
    client.welcomed = True
    client.rate_limit_msgs_per_minute = 2
    with (
        patch.object(client, "_packet_would_fit", return_value=True),
        patch("lxmfy.rrc.client.RNS.Packet") as packet_cls,
    ):
        packet_cls.return_value = MagicMock()
        client.send_message("lobby", "one")
        client.send_message("lobby", "two")
        with pytest.raises(RuntimeError, match="rate limit"):
            client.send_message("lobby", "three")


def test_mention_word_boundary():
    events = []
    client = _client(events)
    peer = bytes(range(32, 48))
    env = make_envelope(
        T_MSG,
        src=peer,
        room="lobby",
        body="notatestbot but @TestBot yes",
        nick="alice",
    )
    client._on_packet(encode_envelope(env))
    msgs = [p for e, p in events if e == "msg"]
    assert msgs and msgs[0].mention is True

    events.clear()
    env2 = make_envelope(
        T_MSG,
        src=peer,
        room="lobby",
        body="email testbot@example.com",
        nick="alice",
    )
    client._on_packet(encode_envelope(env2))
    msgs = [p for e, p in events if e == "msg"]
    assert msgs and msgs[0].mention is False


def test_resource_envelope_expectation():
    from lxmfy.rrc.constants import (
        B_RES_ENCODING,
        B_RES_ID,
        B_RES_KIND,
        B_RES_SHA256,
        B_RES_SIZE,
        T_RESOURCE_ENVELOPE,
    )

    client = _client()
    rid = b"12345678"
    body = {
        B_RES_ID: rid,
        B_RES_KIND: "motd",
        B_RES_SIZE: 5,
        B_RES_SHA256: __import__("hashlib").sha256(b"hello").digest(),
        B_RES_ENCODING: "utf-8",
    }
    env = make_envelope(T_RESOURCE_ENVELOPE, src=bytes(range(16, 32)), body=body)
    client._on_packet(encode_envelope(env))
    assert rid in client._resource_expectations
    assert client._resource_expectations[rid]["kind"] == "motd"


def test_manager_send_action_and_persist(tmp_path):
    from lxmfy.storage import JSONStorage, Storage

    identity = MagicMock()
    identity.hash = _src()
    storage = Storage(JSONStorage(str(tmp_path / "store")))
    manager = RRCManager(
        identity=identity,
        nick="MgrBot",
        auto_reconnect=False,
        storage=storage,
        persist_sessions=True,
    )
    hub = bytes(range(16, 32)).hex()
    with patch.object(RRCClient, "connect"):
        client = manager.connect(hub, rooms=["lobby"])
        client.rooms.add("lobby")
        manager.save_sessions()

    saved = storage.get("rrc_sessions", [])
    assert saved and saved[0]["hub_hash"] == hub
    assert "lobby" in saved[0]["rooms"]

    client.link = MagicMock()
    client.link.status = RNS.Link.ACTIVE
    client.welcomed = True
    client.status = STATUS_CONNECTED
    with (
        patch.object(client, "_packet_would_fit", return_value=True),
        patch("lxmfy.rrc.client.RNS.Packet") as packet_cls,
    ):
        packet_cls.return_value = MagicMock()
        mid = manager.send_action("lobby", "waves", hub_hash=hub)
        assert isinstance(mid, bytes)

    with (
        patch.object(client, "_packet_would_fit", return_value=True),
        patch("lxmfy.rrc.client.RNS.Packet") as packet_cls,
    ):
        packet_cls.return_value = MagicMock()
        manager.join("ops", hub_hash=hub)

    saved = storage.get("rrc_sessions", [])
    assert "ops" in saved[0]["rooms"] or "ops" in client._rejoin_rooms


def test_save_sessions_includes_auto_join_rooms(tmp_path):
    from lxmfy.storage import JSONStorage, Storage

    identity = MagicMock()
    identity.hash = _src()
    storage = Storage(JSONStorage(str(tmp_path / "store2")))
    manager = RRCManager(
        identity=identity,
        nick="MgrBot",
        auto_reconnect=False,
        storage=storage,
        persist_sessions=True,
    )
    hub = bytes(range(16, 32)).hex()
    with patch.object(RRCClient, "connect"):
        client = manager.connect(hub, rooms=["general"])
    saved = storage.get("rrc_sessions", [])
    assert saved[0]["rooms"] == ["general"]
    assert "general" in client._auto_join_rooms
    assert "general" in client._rejoin_rooms
