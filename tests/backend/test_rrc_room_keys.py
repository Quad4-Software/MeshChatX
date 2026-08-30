# SPDX-License-Identifier: 0BSD

"""Tests for RRC +k room key crypto, storage, hub checks, and API."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager
from meshchatx.src.backend.rrc.room_key_crypto import (
    decrypt_room_key,
    encrypt_room_key,
    room_keys_equal,
)
from meshchatx.src.backend.rrc.server import RRCHubServer, _Session

HUB_HASH_HEX = "00112233445566778899aabbccddeeff"
HUB_HASH = bytes.fromhex(HUB_HASH_HEX)
PRIVATE_A = b"identity-private-key-aaaa"
PRIVATE_B = b"identity-private-key-bbbb"


class _Identity:
    def __init__(self, hash_bytes, private_key):
        self.hash = hash_bytes
        self._private_key = private_key

    def get_private_key(self):
        return self._private_key


class _FakeLink:
    def __init__(self, identity):
        self._identity = identity

    def get_remote_identity(self):
        return self._identity


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(json_body=None, match_info=None):
    request = MagicMock()

    async def _json():
        return json_body if json_body is not None else {}

    request.json = _json
    request.match_info = match_info or {}
    request.query = {}
    return request


def test_encrypt_decrypt_roundtrip():
    nonce, ciphertext = encrypt_room_key(PRIVATE_A, "  secret-key  ")
    assert decrypt_room_key(PRIVATE_A, nonce, ciphertext) == "secret-key"
    assert b"secret-key" not in ciphertext
    assert b"secret" not in ciphertext


def test_decrypt_fails_for_other_identity():
    nonce, ciphertext = encrypt_room_key(PRIVATE_A, "secret-key")
    with pytest.raises(Exception):
        decrypt_room_key(PRIVATE_B, nonce, ciphertext)


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        None,
        123,
        "x" * 300,
    ],
)
def test_encrypt_rejects_invalid_keys(bad):
    with pytest.raises((TypeError, ValueError)):
        encrypt_room_key(PRIVATE_A, bad)


@given(
    left=st.text(min_size=1, max_size=32).filter(lambda s: bool(s.strip())),
    pad_l=st.integers(min_value=0, max_value=3),
    pad_r=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=40, deadline=None)
def test_property_room_keys_equal_strips(left, pad_l, pad_r):
    expected = left.strip()
    provided = (" " * pad_l) + expected + (" " * pad_r)
    assert room_keys_equal(provided, expected) is True
    assert room_keys_equal(expected + "x", expected) is False
    assert room_keys_equal(None, expected) is False


def test_dao_upsert_get_delete(db):
    nonce, ciphertext = encrypt_room_key(PRIVATE_A, "alpha")
    db.rrc_room_keys.upsert(HUB_HASH_HEX, "rrc.hub", "lobby", nonce, ciphertext)
    row = db.rrc_room_keys.get(HUB_HASH_HEX, "rrc.hub", "lobby")
    assert row is not None
    assert decrypt_room_key(PRIVATE_A, row["nonce"], row["ciphertext"]) == "alpha"

    nonce2, ciphertext2 = encrypt_room_key(PRIVATE_A, "beta")
    db.rrc_room_keys.upsert(HUB_HASH_HEX, "rrc.hub", "lobby", nonce2, ciphertext2)
    row2 = db.rrc_room_keys.get(HUB_HASH_HEX, "rrc.hub", "lobby")
    assert decrypt_room_key(PRIVATE_A, row2["nonce"], row2["ciphertext"]) == "beta"

    listed = db.rrc_room_keys.list_for_hub(HUB_HASH_HEX, "rrc.hub")
    assert len(listed) == 1
    assert "ciphertext" not in listed[0].keys() or listed[0].get("ciphertext") is None

    assert db.rrc_room_keys.delete(HUB_HASH_HEX, "rrc.hub", "lobby") == 1
    assert db.rrc_room_keys.get(HUB_HASH_HEX, "rrc.hub", "lobby") is None


def test_manager_remember_get_forget(db, tmp_path):
    identity = _Identity(b"\x11" * 16, PRIVATE_A)
    manager = RRCManager(identity, str(tmp_path), database=db)
    hub = manager.add_hub(HUB_HASH, name="Hub")
    manager.remember_room_key(hub, "Lobby", "correct-horse")
    assert manager.get_room_key(hub, "lobby") == "correct-horse"
    assert manager.has_stored_room_key(hub, "lobby") is True
    keys = manager.list_stored_room_keys(hub)
    assert keys == [
        {
            "hub_hash": HUB_HASH_HEX,
            "dest_name": "rrc.hub",
            "room": "lobby",
            "updated_at": keys[0]["updated_at"],
        },
    ]
    assert "key" not in keys[0]
    assert manager.forget_room_key(hub, "lobby") == 1
    assert manager.get_room_key(hub, "lobby") is None


def test_manager_wrong_identity_returns_none(db, tmp_path):
    manager_a = RRCManager(
        _Identity(b"\x11" * 16, PRIVATE_A),
        str(tmp_path),
        database=db,
    )
    hub = manager_a.add_hub(HUB_HASH)
    manager_a.remember_room_key(hub, "lobby", "secret")

    manager_b = RRCManager(
        _Identity(b"\x22" * 16, PRIVATE_B),
        str(tmp_path),
        database=db,
    )
    hub_b = manager_b.add_hub(HUB_HASH)
    assert manager_b.get_room_key(hub_b, "lobby") is None
    assert manager_b.has_stored_room_key(hub_b, "lobby") is True


def test_bad_key_error_detector():
    assert RRCManager.is_bad_key_error("bad key (+k)") is True
    assert RRCManager.is_bad_key_error("ERROR: Bad Key (+K)") is True
    assert RRCManager.is_bad_key_error("invite-only (+i)") is False
    assert RRCManager.is_bad_key_error("failed: enable +k first") is False
    assert RRCManager.is_bad_key_error("+k") is False
    assert RRCManager.is_bad_key_error(None) is False


def test_redact_mode_plus_k_for_history():
    assert (
        RRCHub._redact_command_for_history("/mode vault +k supersecret")
        == "/mode vault +k ***"
    )
    assert RRCHub._redact_command_for_history("/who lobby") == "/who lobby"
    assert RRCHub._redact_command_for_history("/mode vault -k") == "/mode vault -k"


def test_handle_error_forgets_bad_key(db, tmp_path):
    identity = _Identity(b"\x11" * 16, PRIVATE_A)
    manager = RRCManager(identity, str(tmp_path), database=db)
    hub = manager.add_hub(HUB_HASH)
    manager.remember_room_key(hub, "lobby", "wrong")
    with hub._lock:
        hub._pending_joins.add("lobby")
        hub.rooms.add("lobby")

    hub._handle_error(
        proto.make_envelope(
            proto.T_ERROR,
            src=HUB_HASH,
            room="lobby",
            body="bad key (+k)",
        ),
    )
    assert manager.get_room_key(hub, "lobby") is None
    assert "lobby" not in hub.rooms


def test_welcome_rejoin_uses_stored_key(db, tmp_path, monkeypatch):
    identity = _Identity(b"\x11" * 16, PRIVATE_A)
    manager = RRCManager(identity, str(tmp_path), database=db)
    hub = manager.add_hub(HUB_HASH)
    hub.add_room("secret")
    manager.remember_room_key(hub, "secret", "hunter2")

    seen = {}

    def _fake_join(room, key=None, silent=False):
        seen["room"] = room
        seen["key"] = key
        seen["silent"] = silent

    monkeypatch.setattr(hub, "join_room", _fake_join)
    manager._on_welcome(hub)
    assert seen == {"room": "secret", "key": "hunter2", "silent": True}


def test_hub_rejects_wrong_key_and_accepts_correct():
    owner = _Identity(HUB_HASH, PRIVATE_A)
    server = RRCHubServer(MagicMock(), owner, name="Keyed Hub")
    server.register_room("vault", key="correct")
    cfg = server.rooms.room_config_for_api("vault")
    assert cfg["has_key"] is True
    assert "key" not in cfg

    peer = _Identity(b"\xaa" * 16, b"peer-key")
    link = _FakeLink(peer)
    sess = _Session()
    sess.peer = peer.hash
    sess.nick = "alice"
    sess.welcomed = True
    server._sessions[link] = sess

    bad_out = []
    server._route(
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=peer.hash, room="vault", body="wrong"),
        bad_out,
    )
    bad_envs = [proto.decode(payload) for _, payload in bad_out]
    assert any(
        e[proto.K_T] == proto.T_ERROR and e[proto.K_BODY] == "bad key (+k)"
        for e in bad_envs
    )
    assert "vault" not in sess.rooms
    assert server.rooms.ensure_state("vault").get("founder") is None

    good_out = []
    server._route(
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=peer.hash, room="vault", body="correct"),
        good_out,
    )
    good_envs = [proto.decode(payload) for _, payload in good_out]
    assert any(e[proto.K_T] == proto.T_JOINED for e in good_envs)
    assert server.rooms.is_room_op("vault", peer.hash) is True


def test_hub_invite_only_checked_before_founder_promotion():
    owner = _Identity(HUB_HASH, PRIVATE_A)
    server = RRCHubServer(MagicMock(), owner, name="Invite Hub")
    server.register_room("private", invite_only=True)
    peer = _Identity(b"\xbb" * 16, b"peer-key")
    link = _FakeLink(peer)
    sess = _Session()
    sess.peer = peer.hash
    sess.nick = "bob"
    sess.welcomed = True
    server._sessions[link] = sess

    out = []
    server._route(
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=peer.hash, room="private"),
        out,
    )
    envs = [proto.decode(payload) for _, payload in out]
    assert any(
        e[proto.K_T] == proto.T_ERROR and e[proto.K_BODY] == "invite-only (+i)"
        for e in envs
    )
    assert server.rooms.ensure_state("private").get("founder") is None


def test_set_room_key_clear_and_persist(tmp_path):
    owner = _Identity(HUB_HASH, PRIVATE_A)
    server = RRCHubServer(MagicMock(), owner, name="Keyed Hub")
    server.register_room("vault", key="one")
    assert server.rooms.ensure_state("vault")["key"] == "one"
    server.set_room_key("vault", "two")
    assert server.rooms.ensure_state("vault")["key"] == "two"
    server.set_room_key("vault", None)
    assert not server.rooms.ensure_state("vault")["key"]


@pytest.mark.asyncio
async def test_api_store_list_delete_room_key(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))

    put_key = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/key",
        "PUT",
    )
    response = await put_key(
        _make_request(
            json_body={"key": "secret"},
            match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"},
        ),
    )
    assert response.status == 200
    body = json.loads(response.body)
    assert body["has_stored_key"] is True
    assert "secret" not in response.body.decode()

    list_keys = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/room-keys", "GET")
    listing = json.loads(
        (
            await list_keys(
                _make_request(match_info={"hub_hash": HUB_HASH_HEX}),
            )
        ).body,
    )
    assert listing["keys"][0]["room"] == "lobby"
    assert "key" not in listing["keys"][0]
    assert "ciphertext" not in listing["keys"][0]

    delete_key = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/key",
        "DELETE",
    )
    deleted = await delete_key(
        _make_request(match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"}),
    )
    assert deleted.status == 200
    assert json.loads(deleted.body)["deleted"] == 1


@pytest.mark.asyncio
async def test_api_join_offline_remembers_key(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))

    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(
            json_body={"room": "vault", "key": "offline-secret", "remember": True},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert data["has_stored_key"] is True
    assert "offline-secret" not in response.body.decode()

    hub = mock_app.rrc_manager.find_hub(HUB_HASH)
    assert mock_app.rrc_manager.get_room_key(hub, "vault") == "offline-secret"


@pytest.mark.asyncio
async def test_api_join_uses_stored_key_when_connected(mock_app, monkeypatch):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))
    hub = mock_app.rrc_manager.find_hub(HUB_HASH)
    mock_app.rrc_manager.remember_room_key(hub, "vault", "stored-secret")

    with hub._lock:
        hub.status = RRCHub.STATUS_CONNECTED

    seen = {}

    def _fake_join(room, key=None, silent=False):
        seen["room"] = room
        seen["key"] = key

    monkeypatch.setattr(hub, "join_room", _fake_join)

    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(
            json_body={"room": "vault"},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    assert response.status == 200
    assert seen == {"room": "vault", "key": "stored-secret"}


@pytest.mark.asyncio
async def test_api_put_key_rejects_empty(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))
    put_key = _find_handler(
        mock_app,
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/key",
        "PUT",
    )
    response = await put_key(
        _make_request(
            json_body={"key": "  "},
            match_info={"hub_hash": HUB_HASH_HEX, "room": "lobby"},
        ),
    )
    assert response.status == 400


@pytest.mark.asyncio
async def test_api_join_remember_false_skips_storage(mock_app):
    post_hub = _find_handler(mock_app, "/api/v1/rrc/hubs", "POST")
    await post_hub(_make_request(json_body={"hub_hash": HUB_HASH_HEX}))
    join = _find_handler(mock_app, "/api/v1/rrc/hubs/{hub_hash}/rooms", "POST")
    response = await join(
        _make_request(
            json_body={"room": "vault", "key": "ephemeral", "remember": False},
            match_info={"hub_hash": HUB_HASH_HEX},
        ),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert data["has_stored_key"] is False
    hub = mock_app.rrc_manager.find_hub(HUB_HASH)
    assert mock_app.rrc_manager.get_room_key(hub, "vault") is None


@pytest.mark.asyncio
async def test_host_api_set_and_clear_room_key(mock_app):
    create = _find_handler(mock_app, "/api/v1/rrc/servers", "POST")
    created = await create(
        _make_request(json_body={"name": "Host Hub", "enabled": False}),
    )
    assert created.status == 200
    hub_id = json.loads(created.body)["hub"]["id"]

    add_room = _find_handler(mock_app, "/api/v1/rrc/servers/{hub_id}/rooms", "POST")
    room_resp = await add_room(
        _make_request(
            json_body={"name": "vault", "key": "initial"},
            match_info={"hub_id": hub_id},
        ),
    )
    assert room_resp.status == 200
    rooms = json.loads(room_resp.body)["hub"]["rooms"]
    vault = next(r for r in rooms if r["name"] == "vault")
    assert vault["has_key"] is True
    assert "key" not in vault
    assert b"initial" not in room_resp.body

    set_key = _find_handler(
        mock_app,
        "/api/v1/rrc/servers/{hub_id}/rooms/{room}/key",
        "PUT",
    )
    cleared = await set_key(
        _make_request(
            json_body={"key": None},
            match_info={"hub_id": hub_id, "room": "vault"},
        ),
    )
    assert cleared.status == 200
    rooms2 = json.loads(cleared.body)["hub"]["rooms"]
    vault2 = next(r for r in rooms2 if r["name"] == "vault")
    assert vault2["has_key"] is False
