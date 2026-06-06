# SPDX-License-Identifier: 0BSD

"""Unit tests for the RRC hub server (hosting) layer."""

import time

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager, RRCHub
from meshchatx.src.backend.rrc.server import (
    RRCHubServer,
    RRCServerManager,
    _LoopbackEndpoint,
    _Session,
)


class FakeIdentity:
    """Minimal stand-in for an RNS identity."""

    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeLink:
    """Hashable link stand-in with a remote identity."""

    def __init__(self, identity):
        self._identity = identity

    def get_remote_identity(self):
        return self._identity


class FakeManager:
    """Records change notifications instead of broadcasting them."""

    def __init__(self):
        self.changes = 0
        self.history_per_room_cap = 0
        self.identity = FakeIdentity(b"\x22" * 16)
        self._active_hub = None
        self._active_room = None

    def _notify_change(self, hub=None):
        self.changes += 1

    def _notify_messages(self, hub, msg):
        pass

    def active_room_for(self, hub):
        if self._active_hub is hub:
            return self._active_room
        return None

    def save(self):
        pass


HUB_HASH = bytes(range(16))


def make_server(name="Test Hub", greeting=None):
    return RRCHubServer(
        FakeManager(),
        FakeIdentity(HUB_HASH),
        name=name,
        greeting=greeting,
    )


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


def test_hello_returns_welcome():
    server = make_server(greeting="hi there")
    link = FakeLink(FakeIdentity(b"peer-aaaaaaaaaaaa"))
    sess = add_session(server, link, link._identity.hash, welcomed=False)

    env = proto.make_envelope(proto.T_HELLO, src=link._identity.hash, nick="alice")
    out = route(server, link, sess, env)

    assert sess.welcomed is True
    assert sess.nick == "alice"
    welcome = out[0][1]
    assert welcome[proto.K_T] == proto.T_WELCOME
    body = welcome[proto.K_BODY]
    assert body[proto.B_WELCOME_HUB] == "Test Hub"
    assert proto.L_MAX_MSG_BODY_BYTES in body[proto.B_WELCOME_LIMITS]
    # greeting follows the welcome as a notice
    assert out[1][1][proto.K_T] == proto.T_NOTICE
    assert out[1][1][proto.K_BODY] == "hi there"


def test_join_fanout_and_member_list():
    server = make_server()
    link_a = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess_a = add_session(server, link_a, link_a._identity.hash, nick="alice")
    link_b = FakeLink(FakeIdentity(b"bbbbbbbbbbbbbbbb"))
    sess_b = add_session(server, link_b, link_b._identity.hash, nick="bob")

    route(
        server,
        link_a,
        sess_a,
        proto.make_envelope(proto.T_JOIN, src=sess_a.peer, room="lobby"),
    )
    out = route(
        server,
        link_b,
        sess_b,
        proto.make_envelope(proto.T_JOIN, src=sess_b.peer, room="lobby"),
    )

    fanout = [e for lnk, e in out if lnk is link_a and e[proto.K_T] == proto.T_JOINED]
    assert fanout
    assert fanout[0][proto.K_BODY] == [sess_b.peer]
    assert fanout[0][proto.K_NICK] == "bob"

    joined_self = [
        e for lnk, e in out if lnk is link_b and e[proto.K_T] == proto.T_JOINED
    ]
    assert joined_self
    assert set(joined_self[0][proto.K_BODY]) == {sess_a.peer, sess_b.peer}


def test_message_fanout_rewrites_source():
    server = make_server()
    link_a = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess_a = add_session(server, link_a, link_a._identity.hash, nick="alice")
    link_b = FakeLink(FakeIdentity(b"bbbbbbbbbbbbbbbb"))
    sess_b = add_session(server, link_b, link_b._identity.hash, nick="bob")
    route(
        server,
        link_a,
        sess_a,
        proto.make_envelope(proto.T_JOIN, src=sess_a.peer, room="lobby"),
    )
    route(
        server,
        link_b,
        sess_b,
        proto.make_envelope(proto.T_JOIN, src=sess_b.peer, room="lobby"),
    )

    out = route(
        server,
        link_a,
        sess_a,
        proto.make_envelope(proto.T_MSG, src=sess_a.peer, room="lobby", body="hello"),
    )

    recipients = {lnk for lnk, e in out}
    assert recipients == {link_a, link_b}
    for _, e in out:
        assert e[proto.K_SRC] == sess_a.peer
        assert e[proto.K_NICK] == "alice"
        assert e[proto.K_BODY] == "hello"
        assert e[proto.K_ROOM] == "lobby"


def test_message_to_unknown_room_errors():
    server = make_server()
    link = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess = add_session(server, link, link._identity.hash, nick="alice")

    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room="ghost", body="anyone?"),
    )

    assert out[0][1][proto.K_T] == proto.T_ERROR


def test_list_command_matches_client_parser():
    server = make_server()
    server.register_room("general", topic="General chatter")
    server.register_room("secret", topic="hidden", private=True)
    link = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess = add_session(server, link, link._identity.hash, nick="alice")

    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=None, body="/list"),
    )

    text = out[0][1][proto.K_BODY]
    rooms = proto.parse_room_list_notice(text)
    assert rooms == {"general": "General chatter"}


def test_who_command_matches_client_parser():
    server = make_server()
    link = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room="lobby"),
    )

    out = route(
        server,
        link,
        sess,
        proto.make_envelope(
            proto.T_MSG, src=sess.peer, room="lobby", body="/who lobby"
        ),
    )

    notice = [e for _, e in out if e[proto.K_T] == proto.T_NOTICE]
    parsed = proto.parse_who_notice(notice[-1][proto.K_BODY])
    assert parsed is not None
    room, entries = parsed
    assert room == "lobby"
    assert any(nick == "alice" for nick, _ in entries)


def test_part_emits_parted():
    server = make_server()
    link_a = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess_a = add_session(server, link_a, link_a._identity.hash, nick="alice")
    link_b = FakeLink(FakeIdentity(b"bbbbbbbbbbbbbbbb"))
    sess_b = add_session(server, link_b, link_b._identity.hash, nick="bob")
    route(
        server,
        link_a,
        sess_a,
        proto.make_envelope(proto.T_JOIN, src=sess_a.peer, room="lobby"),
    )
    route(
        server,
        link_b,
        sess_b,
        proto.make_envelope(proto.T_JOIN, src=sess_b.peer, room="lobby"),
    )

    out = route(
        server,
        link_a,
        sess_a,
        proto.make_envelope(proto.T_PART, src=sess_a.peer, room="lobby"),
    )

    self_parted = [
        e for lnk, e in out if lnk is link_a and e[proto.K_T] == proto.T_PARTED
    ]
    fanout = [e for lnk, e in out if lnk is link_b and e[proto.K_T] == proto.T_PARTED]
    assert self_parted and fanout
    assert "lobby" not in sess_a.rooms


def test_ping_returns_pong():
    server = make_server()
    link = FakeLink(FakeIdentity(b"aaaaaaaaaaaaaaaa"))
    sess = add_session(server, link, link._identity.hash, welcomed=False)

    out = route(
        server, link, sess, proto.make_envelope(proto.T_PING, src=sess.peer, body=123)
    )

    assert out[0][1][proto.K_T] == proto.T_PONG
    assert out[0][1][proto.K_BODY] == 123


def test_uptime_seconds_in_summary():
    server = make_running_server()
    assert server.to_dict()["uptime_seconds"] == 0
    server._started_at = time.time() - 90
    assert server.to_dict()["uptime_seconds"] >= 90


def test_register_and_unregister_room():
    server = make_server()
    server.register_room("Lobby", topic="hi")
    summary = server.to_dict()
    names = {r["name"] for r in summary["rooms"]}
    assert "lobby" in names
    server.unregister_room("lobby")
    summary = server.to_dict()
    assert all(r["name"] != "lobby" or not r["registered"] for r in summary["rooms"])


class FakeDestination:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeServerManager:
    def __init__(self, hubs):
        self.hubs = hubs

    def _notify_change(self, hub=None):
        pass


def make_running_server(name="Local Hub"):
    server = RRCHubServer(FakeManager(), FakeIdentity(HUB_HASH), name=name)
    server.destination = FakeDestination(b"\x10" * 16)
    server.running = True
    return server


def test_find_local_server_only_when_running(tmp_path):
    server = make_running_server()
    manager = RRCManager(identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path))
    manager.set_server_manager(FakeServerManager([server]))

    assert manager.find_local_server(server.dest_hash) is server
    server.running = False
    assert manager.find_local_server(server.dest_hash) is None


def test_unread_counts_increment_and_clear(tmp_path):
    manager = FakeManager()
    hub = RRCHub(manager, FakeIdentity(HUB_HASH), name="Hub")
    hub._bump_unread("lobby")
    hub._bump_unread("lobby")
    assert hub.unread_counts.get("lobby") == 2
    hub.mark_read("lobby")
    assert hub.unread_counts.get("lobby") is None
    assert "lobby" not in hub.unread_rooms


def test_loopback_hello_and_join(tmp_path):
    server = make_running_server()
    manager = RRCManager(identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path))
    manager.set_server_manager(FakeServerManager([server]))
    hub = manager.add_hub(server.dest_hash)

    link = _LoopbackEndpoint(hub, server)
    server._attach_loopback(link, manager.identity)
    hub.link = link

    hub._send_hello(link)
    assert hub.welcomed is True
    assert hub.status == hub.STATUS_CONNECTED
    assert hub.hub_name == "Local Hub"

    hub.join_room("lobby")
    assert "lobby" in hub.rooms
    assert link in server._room_members["lobby"]


def _loopback_client_hub(tmp_path):
    server = make_running_server()
    server.register_room("general")
    manager = RRCManager(identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path))
    manager.set_server_manager(FakeServerManager([server]))
    hub = manager.add_hub(server.dest_hash)
    link = _LoopbackEndpoint(hub, server)
    server._attach_loopback(link, manager.identity)
    hub.link = link
    hub._send_hello(link)
    assert hub.welcomed is True
    manager.set_active(hub, "general")
    hub.join_room("general", silent=True)
    return server, hub


def test_loopback_command_message_order(tmp_path):
    _, hub = _loopback_client_hub(tmp_path)
    hub.send_command("/help", room="general")
    msgs = hub.messages["general"]
    assert len(msgs) >= 2
    assert msgs[-2].kind == "msg"
    assert msgs[-2].text == "/help"
    assert msgs[-1].kind == "notice"
    assert msgs[-1].text.startswith("commands:")


def test_loopback_nick_command_updates_override(tmp_path):
    _, hub = _loopback_client_hub(tmp_path)
    hub.send_command("/nick bob", room="general")
    assert hub.nick_override == "bob"
    msgs = hub.messages["general"]
    assert msgs[-2].text == "/nick bob"
    assert msgs[-1].text == "nickname set to bob"


def test_server_members_dict_all_and_per_room(tmp_path):
    server = make_running_server()
    server.register_room("general")
    server.register_room("side")
    link_a = object()
    link_b = object()
    sess_a = _Session()
    sess_a.peer = b"\x01" * 16
    sess_a.nick = "alice"
    sess_a.welcomed = True
    sess_a.rooms = {"general"}
    sess_b = _Session()
    sess_b.peer = b"\x02" * 16
    sess_b.nick = "bob"
    sess_b.welcomed = True
    sess_b.rooms = {"general", "side"}
    server._sessions[link_a] = sess_a
    server._sessions[link_b] = sess_b
    server._room_members["general"] = {link_a, link_b}
    server._room_members["side"] = {link_b}

    all_members = server.members_dict()
    assert len(all_members) == 2
    assert {m["name"] for m in all_members} == {"alice", "bob"}

    general_members = server.members_dict("general")
    assert len(general_members) == 2
    assert {m["hash"] for m in general_members} == {
        (b"\x01" * 16).hex(),
        (b"\x02" * 16).hex(),
    }

    side_members = server.members_dict("side")
    assert len(side_members) == 1
    assert side_members[0]["name"] == "bob"
    assert side_members[0]["rooms"] == ["general", "side"]


def test_manager_save_roundtrip(tmp_path):
    manager = RRCServerManager(storage_dir=str(tmp_path))
    hub = RRCHubServer(manager, FakeIdentity(HUB_HASH), name="Saved Hub")
    hub.configure_storage(str(manager._hub_dir(HUB_HASH.hex())))
    hub.register_room("general", topic="chat")
    manager.hubs.append(hub)
    manager.save()

    store = tmp_path / "rrc_server" / "hubs"
    assert store.exists()
    obj = proto.decode(store.read_bytes())
    assert obj["hubs"][0]["name"] == "Saved Hub"
    assert obj["hubs"][0]["rooms"][0]["name"] == "general"
    assert manager.find_hub(HUB_HASH.hex()) is hub
