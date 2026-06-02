# SPDX-License-Identifier: 0BSD

"""Security and abuse-resistance tests for RRC client hub, hosted server, and storage."""

import os
import threading
import time

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager, RRCHub
from meshchatx.src.backend.rrc.server import RRCHubServer, _Session

HUB_HASH = bytes(range(16))


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeManager:
    def __init__(self, nickname=None):
        self.identity = FakeIdentity(b"\xaa" * 16)
        self.filter_loaded_history = False
        self.history_per_room_cap = 0
        self._nickname = nickname

    def get_nickname(self):
        return self._nickname

    def get_name_for_identity_hash(self, _h):
        return None

    def save(self):
        pass

    def _notify_change(self, hub=None):
        pass

    def _notify_messages(self, hub, msg):
        pass

    def set_active(self, hub, room):
        pass

    def _on_welcome(self, hub):
        pass

    def find_local_server(self, _h):
        return None


class FakeLink:
    def __init__(self, identity):
        self._identity = identity

    def get_remote_identity(self):
        return self._identity


def make_client_manager(tmp_path, nickname=None):
    return RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
        get_nickname=(lambda: nickname),
    )


def make_server(rate_per_min=None, max_msg=None, max_rooms=None):
    server = RRCHubServer(
        FakeManager(),
        FakeIdentity(HUB_HASH),
        name="Sec Hub",
    )
    if rate_per_min is not None:
        server.rate_limit_msgs_per_minute = rate_per_min
    if max_msg is not None:
        server.max_msg_body_bytes = max_msg
    if max_rooms is not None:
        server.max_rooms_per_session = max_rooms
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


def test_history_path_stays_under_storage_root(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    malicious_rooms = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "lobby/../../../secret",
        "\x00lobby",
        "/" * 80,
        "a" * 200,
    ]
    root = os.path.realpath(manager._history_root())
    for room in malicious_rooms:
        try:
            normalized = proto.normalize_room(room)
        except ValueError:
            continue
        path = os.path.realpath(manager._history_path(hub, normalized))
        assert path.startswith(root + os.sep) or path == root


def test_corrupted_hub_store_does_not_crash_load(tmp_path):
    manager = make_client_manager(tmp_path)
    store_path = manager._store_path()
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    for payload in [
        b"\xff\xfe",
        b"",
        b"not cbor",
        proto.encode({"hubs": "not a list"}),
    ]:
        with open(store_path, "wb") as f:
            f.write(payload)
        reloaded = make_client_manager(tmp_path)
        reloaded.load()
        assert reloaded.hubs == []


def test_corrupted_history_file_does_not_crash_load(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("lobby")
    hist_path = manager._history_path(hub, "lobby")
    os.makedirs(os.path.dirname(hist_path), exist_ok=True)
    with open(hist_path, "wb") as f:
        f.write(b"\x00\x01garbage")
    hub._load_history()
    assert hub.get_messages("lobby") == []


def test_malformed_packet_bytes_ignored(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    for garbage in [b"", b"\xff", b"\x00" * 64, os.urandom(128)]:
        hub._on_packet(garbage)
    assert hub.get_messages("lobby") == []


def test_non_dict_envelope_ignored(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub._on_packet(proto.encode(["not", "a", "dict"]))
    hub._on_packet(proto.encode(42))
    assert hub.get_messages("lobby") == []


def test_spoofed_src_recorded_on_client(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("lobby")
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"\x99" * 16,
        room="lobby",
        body="spoofed",
        nick="attacker",
    )
    hub._on_packet(proto.encode(env))
    msgs = hub.get_messages("lobby")
    assert len(msgs) == 1
    assert msgs[0].src == b"\x99" * 16


def test_own_echo_suppressed_by_message_id(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("lobby")
    mid = b"12345678"
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


def test_oversized_message_rejected_by_send_message(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.max_msg_body_bytes = 32
    hub.add_room("lobby")
    big = "x" * 100
    with pytest.raises(ValueError, match="too long"):
        hub.send_message("lobby", big)


def test_server_rejects_oversized_message_body():
    server = make_server(max_msg=16)
    link = FakeLink(FakeIdentity(b"\x01" * 16))
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
            proto.T_MSG,
            src=sess.peer,
            room="lobby",
            body="x" * 64,
        ),
    )
    assert out[0][1][proto.K_T] == proto.T_ERROR
    assert "large" in out[0][1][proto.K_BODY].lower()


def test_server_rejects_message_to_unknown_room():
    server = make_server()
    link = FakeLink(FakeIdentity(b"\x02" * 16))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(
            proto.T_MSG,
            src=sess.peer,
            room="nonexistent",
            body="hello",
        ),
    )
    assert out[0][1][proto.K_T] == proto.T_ERROR


def test_server_rate_limits_flood():
    server = make_server(rate_per_min=2)
    link = FakeLink(FakeIdentity(b"\x03" * 16))
    sess = add_session(server, link, link._identity.hash, nick="flooder")
    sess.tokens = 0.0
    sess.last_refill = time.monotonic()
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room="lobby", body="/help"),
    )
    assert out[0][1][proto.K_T] == proto.T_ERROR
    assert out[0][1][proto.K_BODY] == "rate limited"


def test_server_unwelcomed_client_only_gets_hello_handling():
    server = make_server()
    link = FakeLink(FakeIdentity(b"\x04" * 16))
    sess = add_session(server, link, link._identity.hash, welcomed=False)
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(
            proto.T_MSG,
            src=sess.peer,
            room="lobby",
            body="should not fanout",
        ),
    )
    assert not any(e[proto.K_T] == proto.T_MSG for _, e in out)


def test_server_max_rooms_per_session_enforced():
    server = make_server(max_rooms=2)
    link = FakeLink(FakeIdentity(b"\x05" * 16))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room="one"),
    )
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room="two"),
    )
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room="three"),
    )
    assert out[0][1][proto.K_T] == proto.T_ERROR
    assert "too many" in out[0][1][proto.K_BODY].lower()


def test_server_rewrites_message_source_to_session_peer():
    server = make_server()
    link_a = FakeLink(FakeIdentity(b"\x06" * 16))
    sess_a = add_session(server, link_a, link_a._identity.hash, nick="alice")
    link_b = FakeLink(FakeIdentity(b"\x07" * 16))
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
    fake_src = b"\xff" * 16
    out = route(
        server,
        link_a,
        sess_a,
        proto.make_envelope(
            proto.T_MSG,
            src=fake_src,
            room="lobby",
            body="hello",
        ),
    )
    for _, env in out:
        if env[proto.K_T] == proto.T_MSG:
            assert env[proto.K_SRC] == sess_a.peer


def test_server_long_room_name_rejected():
    server = make_server()
    server.max_room_name_bytes = 8
    link = FakeLink(FakeIdentity(b"\x08" * 16))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(
            proto.T_JOIN,
            src=sess.peer,
            room="a" * 32,
        ),
    )
    assert out[0][1][proto.K_T] == proto.T_ERROR


def test_server_invalid_cbor_packet_silently_dropped():
    server = make_server()
    link = FakeLink(FakeIdentity(b"\x09" * 16))
    add_session(server, link, link._identity.hash, welcomed=False)
    server._on_packet(link, os.urandom(64))
    assert link in server._sessions
    assert server.client_count() == 0


def test_server_concurrent_packets_do_not_corrupt_state():
    server = make_server()
    link = FakeLink(FakeIdentity(b"\x0a" * 16))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room="lobby"),
    )

    def spam():
        for _ in range(20):
            server._on_packet(
                link,
                proto.encode(
                    proto.make_envelope(
                        proto.T_PING,
                        src=sess.peer,
                        body=os.urandom(4),
                    ),
                ),
            )

    threads = [threading.Thread(target=spam) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive()


def test_who_notice_malformed_hash_prefix_ignored(tmp_path):
    manager = make_client_manager(tmp_path)
    hub = manager.add_hub(bytes(range(16)))
    hub.add_room("lobby")
    env = proto.make_envelope(
        proto.T_NOTICE,
        src=None,
        body="members in lobby: not-a-hex (zzzzzzzzzzzz), alice (aabbccddeeff)",
    )
    hub._on_packet(proto.encode(env))
    assert hub.get_members("lobby") == []


def test_private_room_excluded_from_list_output():
    server = make_server()
    server.register_room("public", topic="open")
    server.register_room("secret", topic="hidden", private=True)
    link = FakeLink(FakeIdentity(b"\x0b" * 16))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=None, body="/list"),
    )
    text = out[0][1][proto.K_BODY]
    rooms = proto.parse_room_list_notice(text)
    assert "public" in rooms
    assert "secret" not in rooms


def test_hub_status_constants_stable():
    assert RRCHub.STATUS_DISCONNECTED == 0
    assert RRCHub.STATUS_CONNECTED == 2
