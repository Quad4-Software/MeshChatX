# SPDX-License-Identifier: 0BSD

"""Unit tests for the RRC protocol and manager layers."""

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager


class FakeIdentity:
    """Minimal stand-in for an RNS identity."""

    def __init__(
        self,
        hash_bytes=b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",
    ):
        self.hash = hash_bytes


def make_manager(tmp_path, nickname=None):
    return RRCManager(
        identity=FakeIdentity(),
        storage_dir=str(tmp_path),
        get_nickname=(lambda: nickname),
    )


def test_envelope_roundtrip():
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"abcd",
        room="Lobby",
        body="hello",
        nick="bob",
        mid=b"12345678",
        ts=42,
    )
    assert env[proto.K_T] == proto.T_MSG
    assert env[proto.K_ROOM] == "Lobby"
    decoded = proto.decode(proto.encode(env))
    assert decoded == env


def test_normalize_room():
    assert proto.normalize_room("  LoBBy ") == "lobby"


def test_normalize_room_empty_raises():
    import pytest

    with pytest.raises(ValueError):
        proto.normalize_room("   ")


def test_mentions():
    assert proto.text_mentions("hey @Alice, hi", "alice")
    assert not proto.text_mentions("hey alice", "alice")
    assert not proto.text_mentions("hey @alicebob", "alice")
    assert not proto.text_mentions("anything", "")


def test_parse_who_notice():
    parsed = proto.parse_who_notice(
        "members in lobby: alice (aabbccddeeff), aabbccddeeff00112233445566778899",
    )
    assert parsed is not None
    room, entries = parsed
    assert room == "lobby"
    assert ("alice", "aabbccddeeff") in entries
    assert (None, "aabbccddeeff00112233445566778899") in entries


def test_parse_who_notice_rejects_other_text():
    assert proto.parse_who_notice("hello world") is None


def test_parse_room_list_notice():
    parsed = proto.parse_room_list_notice(
        "Registered public rooms\nlobby - The lobby\nrandom",
    )
    assert parsed == {"lobby": "The lobby", "random": None}
    assert proto.parse_room_list_notice("No public rooms registered") == {}
    assert proto.parse_room_list_notice("unrelated") is None


def test_message_to_dict():
    msg = proto.RRCMessage("msg", "lobby", b"\xaa\xbb", "bob", "hi", 123)
    msg.mention = True
    assert msg.to_dict() == {
        "kind": "msg",
        "room": "lobby",
        "src": "aabb",
        "nick": "bob",
        "text": "hi",
        "ts": 123,
        "mention": True,
    }


def test_manager_add_and_find_hub(tmp_path):
    manager = make_manager(tmp_path)
    hub_hash = bytes(range(16))
    hub = manager.add_hub(hub_hash, name="Test Hub")
    assert manager.find_hub(hub_hash) is hub
    assert manager.find_hub_by_hex(hub_hash.hex()) is hub
    assert manager.find_hub_by_hex("not-hex") is None

    # adding the same hub again returns the existing instance
    assert manager.add_hub(hub_hash) is hub

    payload = manager.to_dict()
    assert len(payload["hubs"]) == 1
    assert payload["hubs"][0]["name"] == "Test Hub"
    assert payload["hubs"][0]["hub_hash"] == hub_hash.hex()


def test_manager_save_and_load_roundtrip(tmp_path):
    manager = make_manager(tmp_path)
    hub_hash = bytes(range(16))
    hub = manager.add_hub(hub_hash, name="Persisted")
    hub.add_room("lobby")
    hub.set_auto_reconnect(True)
    hub.set_nick_override("nickname")
    hub.set_hub_icon("satellite-uplink")

    reloaded = make_manager(tmp_path)
    reloaded.load()
    assert len(reloaded.hubs) == 1
    loaded = reloaded.hubs[0]
    assert loaded.hub_hash == hub_hash
    assert "lobby" in loaded.rooms
    assert loaded.auto_reconnect is True
    assert loaded.nick_override == "nickname"
    assert loaded.get_hub_icon() == "satellite-uplink"


def test_hub_room_order_persisted(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("beta")
    hub.add_room("alpha")
    hub.reorder_rooms(["beta", "alpha"])
    manager.save()

    reloaded = make_manager(tmp_path)
    reloaded.load()
    loaded = reloaded.hubs[0]
    assert loaded.ordered_known_rooms()[:2] == ["beta", "alpha"]


def test_hub_icon_rejects_invalid_name(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    with pytest.raises(ValueError):
        hub.set_hub_icon("Not Valid!")


def test_connect_auto_reconnect_hubs_after_load(tmp_path, monkeypatch):
    manager = make_manager(tmp_path)
    hub_hash = bytes(range(16))
    hub = manager.add_hub(hub_hash, name="Persisted")
    hub.set_auto_reconnect(True)
    manager.save()

    reloaded = make_manager(tmp_path)
    reloaded.load()
    loaded = reloaded.hubs[0]
    calls = []

    def fake_connect():
        calls.append(loaded)

    monkeypatch.setattr(loaded, "connect", fake_connect)
    reloaded.connect_auto_reconnect_hubs()
    assert calls == [loaded]

    hub.set_auto_reconnect(False)
    manager.save()
    reloaded2 = make_manager(tmp_path)
    reloaded2.load()
    calls.clear()
    monkeypatch.setattr(reloaded2.hubs[0], "connect", lambda: calls.append(1))
    reloaded2.connect_auto_reconnect_hubs()
    assert calls == []


def test_hub_records_incoming_message_and_unread(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"\x10" * 16,
        room="lobby",
        body="hello there",
        nick="carol",
    )
    hub._on_packet(proto.encode(env))

    messages = hub.get_messages("lobby")
    assert len(messages) == 1
    assert messages[0].text == "hello there"
    assert messages[0].nick == "carol"
    assert "lobby" in hub.unread_rooms


def test_hub_detects_mention(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"\x20" * 16,
        room="lobby",
        body="hey @alice look",
        nick="carol",
    )
    hub._on_packet(proto.encode(env))

    messages = hub.get_messages("lobby")
    assert messages[0].mention is True
    assert "lobby" in hub.mention_rooms


def test_hub_ignores_own_echoed_message(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    mid = b"deadbeef"
    hub._sent_ids.append(mid)
    env = proto.make_envelope(
        proto.T_MSG,
        src=manager.identity.hash,
        room="lobby",
        body="echo",
        mid=mid,
    )
    hub._on_packet(proto.encode(env))
    assert hub.get_messages("lobby") == []


def test_hub_notice_updates_room_list(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    env = proto.make_envelope(
        proto.T_NOTICE,
        src=None,
        body="Registered public rooms\nlobby - Main\nrandom",
    )
    hub._on_packet(proto.encode(env))
    assert hub.available_rooms == {"lobby": "Main", "random": None}


def test_history_is_persisted_and_reloaded(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("lobby")
    msg = proto.RRCMessage("msg", "lobby", b"\x30" * 16, "dave", "persisted text", 100)
    hub._record_message(msg)

    reloaded = make_manager(tmp_path)
    reloaded.load()
    loaded_hub = reloaded.hubs[0]
    messages = loaded_hub.get_messages("lobby")
    assert any(m.text == "persisted text" for m in messages)


def test_status_serialization(tmp_path):
    manager = make_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    data = hub.to_dict()
    assert data["status"] == RRCHub.STATUS_DISCONNECTED
    assert data["connected"] is False
    assert data["rooms"] == []
