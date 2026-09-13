# SPDX-License-Identifier: 0BSD

"""Tests for the /history slash command on hosted RRC hubs."""

import re

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.server import RRCHubServer


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeLink:
    """Hashable link stand-in with a remote identity."""

    def __init__(self, identity):
        self._identity = identity

    def get_remote_identity(self):
        return self._identity


class FakeManager:
    def __init__(self):
        self.identity = FakeIdentity(b"\x22" * 16)
        self.changes = 0

    def _notify_change(self, hub=None):
        self.changes += 1


HUB_HASH = bytes(range(16))
HISTORY_LINE_RE = re.compile(r"^\[\d{2}:\d{2}\] ")


def make_server():
    return RRCHubServer(FakeManager(), FakeIdentity(HUB_HASH), name="Hub")


def add_session(server, peer_hash, nick=None, welcomed=True):
    from meshchatx.src.backend.rrc.server import _Session

    link = FakeLink(FakeIdentity(peer_hash))
    sess = _Session()
    sess.peer = peer_hash
    sess.nick = nick
    sess.welcomed = welcomed
    server._sessions[link] = sess
    return link, sess


def route(server, link, sess, env):
    outgoing = []
    server._route(link, sess, env, outgoing)
    return [(out_link, proto.decode(payload)) for out_link, payload in outgoing]


def join(server, link, sess, room):
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room=room),
    )


def say(server, link, sess, room, text):
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=room, body=text),
    )


def history(server, link, sess, args="", room="lobby"):
    body = "/history" + (" " + args if args else "")
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=room, body=body),
    )


def notices_for(link, out):
    return [
        e[proto.K_BODY]
        for lnk, e in out
        if lnk is link and e.get(proto.K_T) == proto.T_NOTICE
    ]


def test_history_replays_room_log_to_requester_only():
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_b, sess_b = add_session(server, b"\xbb" * 16, nick="bob")
    join(server, link_a, sess_a, "lobby")
    join(server, link_b, sess_b, "lobby")
    say(server, link_a, sess_a, "lobby", "first")
    say(server, link_b, sess_b, "lobby", "second")

    out = history(server, link_a, sess_a)

    # Every queued payload must target the requester only.
    assert all(lnk is link_a for lnk, _ in out)
    notices = notices_for(link_a, out)
    assert notices[0] == "--- history for lobby (2 messages) ---"
    assert notices[-1] == "--- end history ---"
    lines = notices[1:-1]
    assert len(lines) == 2
    assert HISTORY_LINE_RE.match(lines[0])
    assert lines[0].endswith("alice: first")
    assert lines[1].endswith("bob: second")

    # The other member never sees the replay.
    assert notices_for(link_b, out) == []


def test_history_defaults_to_issuing_room():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    join(server, link, sess, "side")
    say(server, link, sess, "lobby", "in lobby")
    say(server, link, sess, "side", "in side")

    out = history(server, link, sess, room="side")
    notices = notices_for(link, out)
    assert notices[0].startswith("--- history for side ")
    assert any(line.endswith("alice: in side") for line in notices)
    assert not any("in lobby" in line for line in notices)


def test_history_explicit_room_requires_membership():
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_b, sess_b = add_session(server, b"\xbb" * 16, nick="bob")
    join(server, link_a, sess_a, "lobby")
    join(server, link_a, sess_a, "private")
    join(server, link_b, sess_b, "lobby")
    say(server, link_a, sess_a, "private", "secret stuff")

    # Member can read another room they joined.
    out = history(server, link_a, sess_a, args="private", room="lobby")
    notices = notices_for(link_a, out)
    assert notices[0] == "--- history for private (1 messages) ---"
    assert any(line.endswith("alice: secret stuff") for line in notices)

    # Non-member cannot read it.
    out = history(server, link_b, sess_b, args="private", room="lobby")
    notices = notices_for(link_b, out)
    assert notices == ["not a member of private"]


def test_history_limit_and_clamping():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    for i in range(60):
        say(server, link, sess, "lobby", f"msg{i}")

    out = history(server, link, sess, args="3")
    notices = notices_for(link, out)
    lines = notices[1:-1]
    assert notices[0] == "--- history for lobby (3 messages) ---"
    assert [line.rsplit(": ", 1)[-1] for line in lines] == ["msg57", "msg58", "msg59"]

    # n clamps to 50 even when more history exists.
    out = history(server, link, sess, args="999")
    notices = notices_for(link, out)
    assert notices[0] == "--- history for lobby (50 messages) ---"
    assert len(notices[1:-1]) == 50
    assert notices[1].endswith("alice: msg10")

    # Explicit room plus count.
    out = history(server, link, sess, args="lobby 2")
    notices = notices_for(link, out)
    assert len(notices[1:-1]) == 2


def test_history_rejects_non_numeric_count():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    say(server, link, sess, "lobby", "hi")

    out = history(server, link, sess, args="lobby banana")
    assert notices_for(link, out) == ["usage: /history [room] [n]"]

    out = history(server, link, sess, args="lobby 5 extra")
    assert notices_for(link, out) == ["usage: /history [room] [n]"]


def test_history_empty_room_and_no_room_context():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")

    out = history(server, link, sess)
    assert notices_for(link, out) == ["no history for lobby"]

    # Issued without a room context there is nothing to read.
    out = history(server, link, sess, room=None)
    assert notices_for(link, out) == ["usage: /history [room] [n]"]


def test_history_records_event():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    say(server, link, sess, "lobby", "hi")

    history(server, link, sess, args="5")

    events = [e for e in server.stats_dict()["events"] if e["type"] == "history"]
    assert len(events) == 1
    assert events[0]["room"] == "lobby"
    assert events[0]["detail"] == "5"
    assert events[0]["peer"] == (b"\xaa" * 16).hex()


def test_history_command_body_not_logged():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    say(server, link, sess, "lobby", "real message")
    history(server, link, sess)

    texts = [e["text"] for e in server._message_log]
    assert texts == ["real message"]


def test_history_clamps_zero_negative_and_huge_counts():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    for i in range(3):
        say(server, link, sess, "lobby", f"m{i}")

    for args in ("0", "-5", "+1"):
        out = history(server, link, sess, args=args)
        assert notices_for(link, out)[0] == "--- history for lobby (1 messages) ---", (
            args
        )

    # int() accepts arbitrarily long digit strings; clamp still applies.
    out = history(server, link, sess, args="9" * 40)
    assert notices_for(link, out)[0] == "--- history for lobby (3 messages) ---"

    # A digit string beyond Python's int limit is not a number at all.
    out = history(server, link, sess, args="9" * 5000)
    assert notices_for(link, out)[0].startswith("bad room")


def test_history_via_notice_envelope():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    say(server, link, sess, "lobby", "hello")

    out = route(
        server,
        link,
        sess,
        proto.make_envelope(
            proto.T_NOTICE, src=sess.peer, room="lobby", body="/history 2"
        ),
    )
    notices = notices_for(link, out)
    assert notices[0] == "--- history for lobby (1 messages) ---"


def test_history_formats_action_and_missing_nick_entries():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16)
    link2, sess2 = add_session(server, b"\xbb" * 16, nick="bob")
    join(server, link, sess, "lobby")
    join(server, link2, sess2, "lobby")
    route(
        server,
        link2,
        sess2,
        proto.make_envelope(proto.T_ACTION, src=sess2.peer, room="lobby", body="waves"),
    )

    out = history(server, link, sess)
    lines = notices_for(link, out)[1:-1]
    assert len(lines) == 1
    assert re.match(r"^\[\d{2}:\d{2}\] \* bob waves$", lines[0])

    # A log entry with no nick falls back to the peer hex prefix.
    server._message_log.append(
        {
            "room": "lobby",
            "ts": "not-a-number",
            "nick": None,
            "peer": "ab" * 16,
            "text": "x",
        }
    )
    out = history(server, link, sess)
    lines = notices_for(link, out)[1:-1]
    assert lines[-1].endswith("abababababab: x")
    assert lines[-1].startswith("[??:??]")


def test_history_non_member_cannot_pull_room_history():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    link2, sess2 = add_session(server, b"\xbb" * 16, nick="bob")
    join(server, link, sess, "lobby")
    say(server, link, sess, "lobby", "member only")

    # bob is not in lobby; without +n he could MSG it, but /history refuses.
    out = history(server, link2, sess2, room="lobby")
    assert notices_for(link2, out) == ["not a member of lobby"]


def test_help_lists_history():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=None, body="/help"),
    )
    assert "/history" in out[0][1][proto.K_BODY]
