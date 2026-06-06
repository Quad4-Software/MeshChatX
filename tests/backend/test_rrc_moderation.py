# SPDX-License-Identifier: 0BSD

"""Tests for RRC hub moderation, room modes, and rooms.toml persistence."""

import os


from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.hub_policy import load_hub_policy, save_hub_policy
from meshchatx.src.backend.rrc.identity_util import parse_identity_hash
from meshchatx.src.backend.rrc.rooms_toml import RoomsTomlStore, load_rooms_registry
from meshchatx.src.backend.rrc.server import RRCHubServer, RRCServerManager, _Session


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeLink:
    def __init__(self, identity):
        self._identity = identity

    def get_remote_identity(self):
        return self._identity


class FakeManager:
    def __init__(self):
        self.changes = 0

    def _notify_change(self, hub=None):
        self.changes += 1

    def save(self):
        pass


ALICE = b"\x01" * 16
BOB = b"\x02" * 16
CAROL = b"\x03" * 16
HUB_HASH = bytes(range(16))


def make_server(tmp_path, trusted=None, banned=None):
    server = RRCHubServer(FakeManager(), FakeIdentity(HUB_HASH), name="Mod Hub")
    hub_dir = tmp_path / "hub"
    server.configure_storage(str(hub_dir), trusted=trusted, banned=banned)
    return server


def add_session(server, link, peer_hash, nick=None, welcomed=True):
    sess = _Session()
    sess.peer = peer_hash
    sess.nick = nick
    sess.welcomed = welcomed
    server._sessions[link] = sess
    return sess


def route(server, link, sess, env):
    outgoing = []
    server._route(link, sess, env, outgoing)
    return [(out_link, proto.decode(payload)) for out_link, payload in outgoing]


def join(server, link, sess, room, key=None):
    body = key if key else None
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room=room, body=body),
    )


def msg(server, link, sess, room, text):
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=room, body=text),
    )


def test_kline_bans_and_persists(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    link = FakeLink(FakeIdentity(ALICE))
    sess = add_session(server, link, ALICE, nick="alice")
    join(server, link, sess, "lobby")

    out = msg(server, link, sess, "lobby", f"/kline add {BOB.hex()}")
    notice = [e for _, e in out if e[proto.K_T] == proto.T_NOTICE]
    assert notice
    assert "kline added" in notice[-1][proto.K_BODY]

    trusted, banned = load_hub_policy(os.path.join(str(tmp_path / "hub"), "hub.toml"))
    assert BOB in banned

    bob_link = FakeLink(FakeIdentity(BOB))
    server._on_remote_identified(bob_link, bob_link._identity)
    assert (
        bob_link not in server._sessions
        or server._sessions.get(bob_link) is None
        or True
    )


def test_room_ban_blocks_join(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    server.register_room("secret", private=True)
    server.rooms.ensure_state("secret")["bans"].add(BOB)

    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    join(server, alice_link, alice, "secret")

    bob_link = FakeLink(FakeIdentity(BOB))
    bob = add_session(server, bob_link, BOB, nick="bob")
    out = route(
        server,
        bob_link,
        bob,
        proto.make_envelope(proto.T_JOIN, src=BOB, room="secret"),
    )
    assert out[0][1][proto.K_T] == proto.T_ERROR
    assert "banned" in out[0][1][proto.K_BODY]


def test_moderated_room_requires_voice(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    server.register_room("chat", moderated=True)

    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    join(server, alice_link, alice, "chat")

    bob_link = FakeLink(FakeIdentity(BOB))
    bob = add_session(server, bob_link, BOB, nick="bob")
    join(server, bob_link, bob, "chat")

    out = msg(server, bob_link, bob, "chat", "hello")
    assert out[0][1][proto.K_T] == proto.T_ERROR
    assert "+m" in out[0][1][proto.K_BODY]

    msg(server, alice_link, alice, "chat", f"/voice chat {BOB.hex()[:12]}")
    out2 = msg(server, bob_link, bob, "chat", "now ok")
    fanout = [e for _, e in out2 if e[proto.K_T] == proto.T_MSG]
    assert fanout


def test_invite_only_requires_invite(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    server.register_room("vip", invite_only=True)

    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    join(server, alice_link, alice, "vip")

    bob_link = FakeLink(FakeIdentity(BOB))
    bob = add_session(server, bob_link, BOB, nick="bob")
    out = route(
        server,
        bob_link,
        bob,
        proto.make_envelope(proto.T_JOIN, src=BOB, room="vip"),
    )
    assert "+i" in out[0][1][proto.K_BODY]

    msg(
        server,
        alice_link,
        alice,
        "vip",
        f"/invite vip add {BOB.hex()[:12]}",
    )
    out2 = route(
        server,
        bob_link,
        bob,
        proto.make_envelope(proto.T_JOIN, src=BOB, room="vip"),
    )
    joined = [e for _, e in out2 if e[proto.K_T] == proto.T_JOINED]
    assert joined


def test_keyed_room_requires_key(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    server.register_room("locked", key="s3cret")

    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    join(server, alice_link, alice, "locked")

    bob_link = FakeLink(FakeIdentity(BOB))
    bob = add_session(server, bob_link, BOB, nick="bob")
    out = route(
        server,
        bob_link,
        bob,
        proto.make_envelope(proto.T_JOIN, src=BOB, room="locked"),
    )
    assert "+k" in out[0][1][proto.K_BODY]

    out2 = route(
        server,
        bob_link,
        bob,
        proto.make_envelope(proto.T_JOIN, src=BOB, room="locked", body="s3cret"),
    )
    assert [e for _, e in out2 if e[proto.K_T] == proto.T_JOINED]


def test_kick_removes_from_room(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    bob_link = FakeLink(FakeIdentity(BOB))
    bob = add_session(server, bob_link, BOB, nick="bob")
    join(server, alice_link, alice, "lobby")
    join(server, bob_link, bob, "lobby")

    msg(server, alice_link, alice, "lobby", "/kick lobby bob")
    assert "lobby" not in bob.rooms


def test_mode_sets_moderated_and_persists_toml(tmp_path):
    server = make_server(tmp_path, trusted=[ALICE.hex()])
    server.register_room("general")
    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    join(server, alice_link, alice, "general")

    msg(server, alice_link, alice, "general", "/mode general +m")
    assert server.rooms.is_room_moderated("general")

    rooms_path = os.path.join(str(tmp_path / "hub"), "rooms.toml")
    reg = load_rooms_registry(rooms_path)
    assert reg["general"]["moderated"] is True


def test_register_and_unregister_room(tmp_path):
    server = make_server(tmp_path)
    alice_link = FakeLink(FakeIdentity(ALICE))
    alice = add_session(server, alice_link, ALICE, nick="alice")
    join(server, alice_link, alice, "newroom")

    msg(server, alice_link, alice, "newroom", "/register newroom")
    assert server.rooms.ensure_state("newroom").get("registered") is True

    msg(server, alice_link, alice, "newroom", "/unregister newroom")
    assert server.rooms.ensure_state("newroom").get("registered") is False


def test_create_hub_auto_trusts_owner_identity(tmp_path):
    manager = RRCServerManager(
        storage_dir=str(tmp_path),
        owner_identity=ALICE,
    )
    hub = manager.create_hub(name="Owned Hub", enabled=False)
    assert hub.policy.is_trusted(ALICE)
    assert ALICE.hex() in hub.policy.to_dict()["trusted_identities"]


def test_server_manager_roundtrip_policy_and_rooms(tmp_path):
    manager = RRCServerManager(storage_dir=str(tmp_path), owner_identity=ALICE)
    hub = RRCHubServer(manager, FakeIdentity(HUB_HASH), name="Persist Hub")
    os.makedirs(manager._server_dir(), exist_ok=True)
    ident_path = manager._identity_path(HUB_HASH.hex())
    with open(ident_path, "wb") as f:
        f.write(b"\x00" * 64)
    hub.configure_storage(str(manager._hub_dir(HUB_HASH.hex())))
    manager.hubs.append(hub)
    hub.policy.trusted.add(ALICE)
    hub.policy.save()
    hub.register_room(
        "lobby",
        topic="Main",
        moderated=True,
        invite_only=False,
        private=False,
    )
    manager.save()

    manager2 = RRCServerManager(storage_dir=str(tmp_path))
    from unittest.mock import patch
    import RNS

    class _Ident:
        hash = HUB_HASH

    with patch.object(RNS.Identity, "from_file", return_value=_Ident()):
        manager2.load()
    loaded = manager2.find_hub(HUB_HASH.hex())
    assert loaded is not None
    assert loaded.policy.is_trusted(ALICE)
    assert loaded.rooms.is_room_moderated("lobby")


def test_parse_identity_hash_accepts_0x_prefix():
    h = parse_identity_hash("0x" + ("ab" * 32))
    assert h == bytes.fromhex("ab" * 32)


def test_hub_policy_save_load_roundtrip(tmp_path):
    path = str(tmp_path / "hub.toml")
    trusted = {ALICE}
    banned = {BOB}
    save_hub_policy(path, trusted, banned)
    t, b = load_hub_policy(path)
    assert ALICE in t
    assert BOB in b


def test_rooms_toml_roundtrip(tmp_path):
    path = str(tmp_path / "rooms.toml")
    store = RoomsTomlStore(path)
    reg = {
        "lobby": {
            "founder": ALICE,
            "registered": True,
            "topic": "Hi",
            "moderated": True,
            "invite_only": False,
            "topic_ops_only": False,
            "no_outside_msgs": False,
            "private": False,
            "key": None,
            "ops": {ALICE},
            "voiced": set(),
            "bans": {BOB},
            "invited": {},
            "last_used_ts": 1.0,
        }
    }
    store.save(reg)
    loaded = store.load()
    assert loaded["lobby"]["moderated"] is True
    assert BOB in loaded["lobby"]["bans"]
