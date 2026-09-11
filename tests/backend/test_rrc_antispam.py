# SPDX-License-Identifier: 0BSD

"""Anti-spam and observability tests for the hosted RRC hub server."""

import time

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.server import RRCHubServer, _LoopbackEndpoint


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeLink:
    """Link stand-in with the callback surface RRCHubServer uses."""

    def __init__(self, identity):
        self._identity = identity
        self.torn_down = False
        self._closed_cb = None

    def get_remote_identity(self):
        return self._identity

    def set_packet_callback(self, cb):
        self._packet_cb = cb

    def set_link_closed_callback(self, cb):
        self._closed_cb = cb

    def set_remote_identified_callback(self, cb):
        self._identified_cb = cb

    def teardown(self):
        self.torn_down = True
        if self._closed_cb is not None:
            self._closed_cb(self)


class FakeManager:
    def __init__(self):
        self.identity = FakeIdentity(b"\x22" * 16)
        self.changes = 0

    def _notify_change(self, hub=None):
        self.changes += 1


HUB_HASH = bytes(range(16))


def make_server():
    return RRCHubServer(FakeManager(), FakeIdentity(HUB_HASH), name="Hub")


def add_session(server, peer_hash, nick=None, welcomed=True):
    link = FakeLink(FakeIdentity(peer_hash))
    server._on_link(link)
    sess = server._sessions[link]
    sess.peer = peer_hash
    sess.nick = nick
    sess.welcomed = welcomed
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


def events_of_type(server, ev_type):
    return [e for e in server.stats_dict()["events"] if e["type"] == ev_type]


def test_control_bucket_limits_join_churn():
    server = make_server()
    server.control_rate_per_minute = 3
    link, sess = add_session(server, b"\xaa" * 16)

    outs = [join(server, link, sess, f"room{i}") for i in range(8)]
    errors = [
        e
        for out in outs
        for _, e in out
        if e.get(proto.K_T) == proto.T_ERROR and e.get(proto.K_BODY) == "rate limited"
    ]
    assert errors, "control bucket must reject JOIN churn"
    assert server._stats["control_drops"] >= 1
    assert len(sess.rooms) <= 3

    # The message bucket is independent: chat still flows.
    sess.rooms.add("lobby")
    server._room_members.setdefault("lobby", set()).add(link)
    sess.ctrl_tokens = 0.0
    out = route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room="lobby", body="hi"),
    )
    assert not [e for _, e in out if e.get(proto.K_BODY) == "rate limited"], (
        "control bucket exhaustion must not block messages"
    )


def test_ping_stays_free_when_control_bucket_empty():
    server = make_server()
    server.control_rate_per_minute = 1
    link, sess = add_session(server, b"\xaa" * 16, welcomed=False)
    sess.ctrl_tokens = 0.0
    for _ in range(5):
        out = route(
            server,
            link,
            sess,
            proto.make_envelope(proto.T_PING, src=sess.peer, body=7),
        )
        assert out[0][1][proto.K_T] == proto.T_PONG
    assert server._stats["control_drops"] == 0


def test_session_cap_drops_extra_links():
    server = make_server()
    server.max_sessions = 2
    link_a = FakeLink(FakeIdentity(b"\xaa" * 16))
    link_b = FakeLink(FakeIdentity(b"\xbb" * 16))
    link_c = FakeLink(FakeIdentity(b"\xcc" * 16))
    server._on_link(link_a)
    server._on_link(link_b)
    server._on_link(link_c)

    assert link_c.torn_down is True
    assert link_c not in server._sessions
    assert len(server._sessions) == 2
    assert server._stats["links_total"] == 3
    assert server._stats["session_cap_drops"] == 1
    ev = events_of_type(server, "session_cap_drop")
    assert len(ev) == 1


def test_per_peer_cap_drops_newest_links():
    server = make_server()
    server.max_sessions_per_peer = 2
    peer = b"\xaa" * 16
    kept = []
    for _ in range(2):
        link = FakeLink(FakeIdentity(peer))
        server._on_link(link)
        server._on_remote_identified(link, FakeIdentity(peer))
        kept.append(link)

    extra = FakeLink(FakeIdentity(peer))
    server._on_link(extra)
    server._on_remote_identified(extra, FakeIdentity(peer))

    assert extra.torn_down is True
    assert extra not in server._sessions
    assert all(link in server._sessions for link in kept)
    assert server._stats["peer_cap_drops"] == 1
    ev = events_of_type(server, "peer_cap_drop")
    assert len(ev) == 1
    assert ev[0]["peer"] == peer.hex()


def test_stats_dict_shape_and_counters():
    server = make_server()
    server._started_at = time.time() - 5
    link, sess = add_session(server, b"\xaa" * 16)
    join(server, link, sess, "lobby")
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room="lobby", body="hi"),
    )

    data = server.stats_dict()
    stats = data["stats"]
    for key in (
        "links_total",
        "links_closed",
        "messages_relayed",
        "rate_limited_drops",
        "control_drops",
        "session_cap_drops",
        "peer_cap_drops",
        "banned_disconnects",
        "kicks",
        "bans",
        "sessions",
        "welcomed",
        "uptime_s",
    ):
        assert key in stats, key
    assert stats["sessions"] == 1
    assert stats["welcomed"] == 1
    assert stats["links_total"] == 1
    assert stats["messages_relayed"] == 1
    assert stats["uptime_s"] >= 5
    assert isinstance(data["events"], list)


def test_event_log_records_join_and_part():
    server = make_server()
    peer = b"\xaa" * 16
    link, sess = add_session(server, peer)
    join(server, link, sess, "lobby")
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_PART, src=sess.peer, room="lobby"),
    )

    events = server.stats_dict()["events"]
    # Newest first.
    assert events[0]["type"] == "part"
    assert events[0]["room"] == "lobby"
    assert events[0]["peer"] == peer.hex()
    joins = events_of_type(server, "join")
    assert len(joins) == 1
    assert joins[0]["room"] == "lobby"


def test_rate_limited_event_throttled_per_session():
    server = make_server()
    peer = b"\xaa" * 16
    link, sess = add_session(server, peer)
    sess.tokens = 0.0

    for _ in range(5):
        out = route(
            server,
            link,
            sess,
            proto.make_envelope(
                proto.T_MSG,
                src=sess.peer,
                room="lobby",
                body="x",
            ),
        )
        assert out[0][1][proto.K_T] == proto.T_ERROR
        assert out[0][1][proto.K_BODY] == "rate limited"

    assert server._stats["rate_limited_drops"] == 5
    assert len(events_of_type(server, "rate_limited")) == 1

    # After the throttle window the next drop records again.
    sess.last_rate_event_ts -= 60.0
    route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room="lobby", body="x"),
    )
    rl = events_of_type(server, "rate_limited")
    assert len(rl) == 2
    assert rl[0]["peer"] == peer.hex()


def test_banned_disconnect_counted():
    server = make_server()
    peer = b"\xaa" * 16
    link, _sess = add_session(server, peer)
    server.policy.add_ban(peer)

    outgoing = []
    server._disconnect_banned(peer, outgoing, "banned")

    assert server._stats["banned_disconnects"] == 1
    ev = events_of_type(server, "banned_disconnect")
    assert len(ev) == 1
    assert ev[0]["peer"] == peer.hex()
    assert link not in server._sessions
    assert server._stats["links_closed"] == 1


def test_moderation_counters_and_events():
    server = make_server()
    peer_op = b"\xaa" * 16
    peer_victim = b"\xbb" * 16
    link_op, sess_op = add_session(server, peer_op, nick="op")
    link_v, sess_v = add_session(server, peer_victim, nick="victim")
    join(server, link_op, sess_op, "lobby")
    join(server, link_v, sess_v, "lobby")

    server.admin_kick_from_room(peer_victim.hex(), "lobby")
    assert server._stats["kicks"] == 1
    kicks = events_of_type(server, "kick")
    assert len(kicks) == 1
    assert kicks[0]["room"] == "lobby"
    assert kicks[0]["peer"] == peer_victim.hex()

    server.admin_room_ban(peer_victim.hex(), "lobby")
    assert server._stats["bans"] == 1
    rbans = events_of_type(server, "room_ban")
    assert len(rbans) == 1
    assert rbans[0]["room"] == "lobby"

    server.admin_hub_ban(peer_victim.hex())
    assert server._stats["bans"] == 2
    assert len(events_of_type(server, "ban")) == 1
    assert server._stats["banned_disconnects"] == 1


def test_event_log_bounded():
    server = make_server()
    for i in range(260):
        server._record_event("join", room=f"r{i}")
    events = server.stats_dict()["events"]
    assert len(events) == 200
    assert events[0]["room"] == "r259"


class FakeClientHub:
    """Loopback client stand-in: just enough surface for _LoopbackEndpoint."""

    def __init__(self, identity):
        self.manager = FakeManager()
        self.manager.identity = identity
        self.closed = False
        self.packets = []

    def _on_packet(self, payload):
        self.packets.append(payload)

    def _on_closed(self, link):
        self.closed = True


def test_loopback_link_survives_peer_cap():
    """The host's own in-process client must not be evicted by the peer cap."""
    server = make_server()
    server.max_sessions_per_peer = 2
    peer = b"\xaa" * 16
    remotes = []
    for _ in range(2):
        link = FakeLink(FakeIdentity(peer))
        server._on_link(link)
        server._on_remote_identified(link, FakeIdentity(peer))
        remotes.append(link)

    client = FakeClientHub(FakeIdentity(peer))
    loop = _LoopbackEndpoint(client, server)
    server._attach_loopback(loop, FakeIdentity(peer))

    assert loop.status == RNS.Link.ACTIVE, "loopback must not be torn down by peer cap"
    assert client.closed is False
    assert loop in server._sessions
    # Loopback links are exempt: the remote sessions stay too.
    assert all(link in server._sessions for link in remotes)
    assert server._stats["peer_cap_drops"] == 0


def test_loopback_does_not_count_against_peer_cap():
    """A loopback session must not shrink the remote-link budget for a peer."""
    server = make_server()
    server.max_sessions_per_peer = 2
    peer = b"\xaa" * 16

    client = FakeClientHub(FakeIdentity(peer))
    loop = _LoopbackEndpoint(client, server)
    server._attach_loopback(loop, FakeIdentity(peer))

    remotes = []
    for _ in range(2):
        link = FakeLink(FakeIdentity(peer))
        server._on_link(link)
        server._on_remote_identified(link, FakeIdentity(peer))
        remotes.append(link)

    assert all(link.torn_down is False for link in remotes), (
        "loopback must not consume the per-peer session budget"
    )
    assert all(link in server._sessions for link in remotes)


def test_peer_cap_enforced_when_peer_learned_from_packet():
    """A link whose identified callback never ran still hits the peer cap."""
    server = make_server()
    server.max_sessions_per_peer = 2
    peer = b"\xaa" * 16
    links = []
    for _ in range(3):
        link = FakeLink(FakeIdentity(peer))
        server._on_link(link)
        links.append(link)

    # _on_remote_identified never fired; peer is learned lazily by _on_packet.
    for link in links:
        server._on_packet(
            link,
            proto.encode(proto.make_envelope(proto.T_HELLO, src=peer)),
        )

    assert links[2].torn_down is True, "third link must be dropped once peer is known"
    assert links[2] not in server._sessions
    assert all(link in server._sessions for link in links[:2])
    assert server._stats["peer_cap_drops"] == 1


def test_identify_on_non_session_link_cannot_evict_sessions():
    """A stale identify for a link with no session must not drop live links."""
    server = make_server()
    server.max_sessions_per_peer = 3
    peer = b"\xaa" * 16
    links = []
    for _ in range(3):
        link = FakeLink(FakeIdentity(peer))
        server._on_link(link)
        server._on_remote_identified(link, FakeIdentity(peer))
        links.append(link)

    # Pretend the cap was lowered (or session drifted) so existing sessions
    # exceed it, then fire a stale identify for a link that is not a session.
    server.max_sessions_per_peer = 2
    stale = FakeLink(FakeIdentity(peer))
    server._on_remote_identified(stale, FakeIdentity(peer))

    assert all(link.torn_down is False for link in links), (
        "identify for a non-session link must not evict real sessions"
    )


def test_admin_kick_tolerates_session_close_race():
    """_on_close popping the link mid-kick must not turn into a KeyError."""
    server = make_server()
    peer_v = b"\xbb" * 16
    link_v, sess_v = add_session(server, peer_v, nick="victim")
    join(server, link_v, sess_v, "lobby")

    class RacingSessions(dict):
        # Simulates _on_close winning the race between the target lookup and
        # the session re-read outside the lock.
        def __getitem__(self, key):
            self.pop(key, None)
            return super().__getitem__(key)

    server._sessions = RacingSessions(server._sessions)

    # Must not raise; the kick proceeds on the session captured under lock.
    assert server.admin_kick_from_room(peer_v.hex(), "lobby") is True
    assert server._stats["kicks"] == 1
