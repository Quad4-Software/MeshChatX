# SPDX-License-Identifier: 0BSD

"""Oracle and exploratory tests for RRC hub/client membership and ACL bugs."""

from __future__ import annotations

import os
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager
from meshchatx.src.backend.rrc.rooms_toml import (
    dump_rooms_registry,
    load_rooms_registry,
)
from meshchatx.src.backend.rrc.server import RRCHubServer, _Session

HUB_HASH = bytes(range(16))


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
        self.identity = FakeIdentity(b"\x22" * 16)
        self.history_per_room_cap = 0
        self.filter_loaded_history = False
        self._active_hub = None
        self._active_room = None
        self.saved = 0

    def get_nickname(self):
        return None

    def get_name_for_identity_hash(self, _h):
        return None

    def save(self):
        self.saved += 1

    def _notify_change(self, hub=None):
        pass

    def _notify_messages(self, hub, msg):
        pass

    def set_active(self, hub, room):
        self._active_hub = hub
        self._active_room = room

    def active_room_for(self, hub):
        if self._active_hub is hub:
            return self._active_room
        return None

    def _on_welcome(self, hub):
        pass

    def find_local_server(self, _h):
        return None

    def is_bad_key_error(self, text):
        return RRCManager.is_bad_key_error(text)

    def forget_room_key(self, hub, room):
        return 0


def make_server(**kwargs):
    return RRCHubServer(
        FakeManager(),
        FakeIdentity(HUB_HASH),
        name="Oracle Hub",
        **kwargs,
    )


def add_session(server, peer_hash, nick=None, welcomed=True):
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


def join(server, link, sess, room, key=None):
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_JOIN, src=sess.peer, room=room, body=key),
    )


def part(server, link, sess, room):
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_PART, src=sess.peer, room=room),
    )


def msg(server, link, sess, room, body):
    return route(
        server,
        link,
        sess,
        proto.make_envelope(proto.T_MSG, src=sess.peer, room=room, body=body),
    )


def envs_of_type(out, msg_type, to_link=None):
    result = []
    for lnk, env in out:
        if to_link is not None and lnk is not to_link:
            continue
        if env.get(proto.K_T) == msg_type:
            result.append(env)
    return result


def test_oracle_phantom_part_does_not_fanout():
    """Non-member PART must not tell real members that someone left."""
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_b, sess_b = add_session(server, b"\xbb" * 16, nick="bob")
    link_c, sess_c = add_session(server, b"\xcc" * 16, nick="carol")
    join(server, link_a, sess_a, "lobby")
    join(server, link_b, sess_b, "lobby")

    out = part(server, link_c, sess_c, "lobby")
    parted_to_members = [
        env
        for lnk, env in out
        if lnk in (link_a, link_b) and env.get(proto.K_T) == proto.T_PARTED
    ]
    assert parted_to_members == [], "phantom PART fanout to real members"
    assert link_a in server._room_members.get("lobby", set())
    assert link_b in server._room_members.get("lobby", set())
    assert "lobby" in sess_a.rooms
    assert "lobby" in sess_b.rooms


def test_oracle_kick_fans_out_parted_and_blocks_with_no_outside():
    """Kick must notify peers. With +n, kicked peers cannot keep messaging."""
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_victim, sess_victim = add_session(server, b"\xbb" * 16, nick="victim")
    join(server, link_op, sess_op, "lobby")
    join(server, link_victim, sess_victim, "lobby")
    assert server.rooms.is_room_op("lobby", sess_op.peer)
    server.rooms.ensure_state("lobby")["no_outside_msgs"] = True

    out = msg(server, link_op, sess_op, "lobby", "/kick lobby victim")
    parted = envs_of_type(out, proto.T_PARTED, to_link=link_op)
    assert parted, "remaining members must see PARTED after kick"
    assert "lobby" not in sess_victim.rooms
    assert link_victim not in server._room_members.get("lobby", set())

    kicked_err = [
        env
        for lnk, env in out
        if lnk is link_victim and env.get(proto.K_T) == proto.T_ERROR
    ]
    assert kicked_err
    assert "kicked" in kicked_err[0][proto.K_BODY].lower()

    after = msg(server, link_victim, sess_victim, "lobby", "still here")
    assert envs_of_type(after, proto.T_ERROR, to_link=link_victim)
    assert not any(
        env.get(proto.K_T) == proto.T_MSG and env.get(proto.K_BODY) == "still here"
        for lnk, env in after
        if lnk is link_op
    )


def test_oracle_client_kick_error_leaves_joined_room(tmp_path):
    """Client must drop a joined room when hub says kicked/banned."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    hub.rooms.add("lobby")
    hub.members["lobby"] = {b"\x11" * 16, b"\xaa" * 16}
    hub.messages["lobby"] = []
    hub.unread_counts["lobby"] = 4
    hub.unread_rooms.add("lobby")
    hub.mention_rooms.add("lobby")
    hub._handle_error(
        proto.make_envelope(
            proto.T_ERROR,
            src=HUB_HASH,
            room="lobby",
            body="kicked from lobby",
        ),
    )
    assert "lobby" not in hub.rooms
    assert "lobby" not in hub.members
    assert "lobby" not in hub.unread_counts
    assert "lobby" not in hub.unread_rooms
    assert "lobby" not in hub.mention_rooms
    assert "lobby" not in hub.messages
    assert "lobby" not in hub.ordered_known_rooms()


def test_oracle_invite_only_rollback_clears_unread(tmp_path):
    """Failed auto-rejoin (+i) must not leave unread badges for a dropped room."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    hub.rooms.add("private")
    hub.messages["private"] = []
    hub.unread_counts["private"] = 2
    hub.unread_rooms.add("private")
    hub._pending_joins.add("private")
    hub._handle_error(
        proto.make_envelope(
            proto.T_ERROR,
            src=HUB_HASH,
            room="private",
            body="invite-only (+i)",
        ),
    )
    assert "private" not in hub.rooms
    assert "private" not in hub.unread_counts
    assert "private" not in hub.unread_rooms
    assert "private" not in hub.messages
    assert "private" not in hub.ordered_known_rooms()


def test_oracle_client_ban_error_drops_known_room(tmp_path):
    """Ban ERROR must drop the room from the sidebar the same way PART does."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    hub.rooms.add("lobby")
    hub.messages["lobby"] = []
    hub.members["lobby"] = {b"\x11" * 16}
    hub._handle_error(
        proto.make_envelope(
            proto.T_ERROR,
            src=HUB_HASH,
            room="lobby",
            body="banned from lobby",
        ),
    )
    assert "lobby" not in hub.rooms
    assert "lobby" not in hub.messages
    assert "lobby" not in hub.ordered_known_rooms()


def test_oracle_register_room_key_strips_like_join_paths():
    """Hub key store paths must agree with JOIN after strip."""
    server = make_server()
    server.register_room("vault", key="  secret  ")
    stored = server.rooms.ensure_state("vault")["key"]
    assert stored == "secret"

    link, sess = add_session(server, b"\xdd" * 16, nick="dee")
    good = join(server, link, sess, "vault", key="secret")
    assert envs_of_type(good, proto.T_JOINED, to_link=link)

    link2, sess2 = add_session(server, b"\xee" * 16, nick="ee")
    wrong = join(server, link2, sess2, "vault", key="nope")
    assert any(
        e.get(proto.K_BODY) == "bad key (+k)"
        for e in envs_of_type(wrong, proto.T_ERROR)
    )


def test_oracle_topic_private_hides_from_outsiders_and_blocks_set():
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_spy, sess_spy = add_session(server, b"\xbb" * 16, nick="spy")
    server.register_room("secret", private=True, founder=sess_a.peer, topic="hidden")
    join(server, link_a, sess_a, "secret")

    read = msg(server, link_spy, sess_spy, "lobby", "/topic secret")
    notices = envs_of_type(read, proto.T_NOTICE, to_link=link_spy)
    assert notices
    assert notices[0][proto.K_BODY] == "topic for secret: (none)"

    vandal = msg(server, link_spy, sess_spy, "lobby", "/topic secret owned")
    assert envs_of_type(vandal, proto.T_ERROR, to_link=link_spy)
    assert server.rooms.get_state("secret")["topic"] == "hidden"


def test_oracle_topic_read_does_not_create_ghost_state():
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    msg(server, link, sess, "lobby", "/topic ghostroom")
    assert server.rooms.get_state("ghostroom") is None


def test_oracle_who_on_private_room_requires_membership():
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_spy, sess_spy = add_session(server, b"\xbb" * 16, nick="spy")
    server.register_room("secret", private=True, founder=sess_a.peer)
    join(server, link_a, sess_a, "secret")

    out = msg(server, link_spy, sess_spy, "secret", "/who secret")
    notices = envs_of_type(out, proto.T_NOTICE, to_link=link_spy)
    assert notices
    # Outsiders must not learn that a private room exists (same as empty room).
    assert notices[0][proto.K_BODY] == "members in secret: (none)"
    assert "alice" not in notices[0][proto.K_BODY].lower()

    member_out = msg(server, link_a, sess_a, "secret", "/who secret")
    member_notices = envs_of_type(member_out, proto.T_NOTICE, to_link=link_a)
    assert member_notices
    assert "alice" in member_notices[0][proto.K_BODY].lower()


def test_oracle_who_private_existence_oracle_closed():
    """Private registered vs nonexistent must look identical to outsiders."""
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_spy, sess_spy = add_session(server, b"\xbb" * 16, nick="spy")
    server.register_room("secret", private=True, founder=sess_a.peer)
    join(server, link_a, sess_a, "secret")

    private_out = msg(server, link_spy, sess_spy, "lobby", "/who secret")
    missing_out = msg(server, link_spy, sess_spy, "lobby", "/who nosuch")
    private_body = envs_of_type(private_out, proto.T_NOTICE, to_link=link_spy)[0][
        proto.K_BODY
    ]
    missing_body = envs_of_type(missing_out, proto.T_NOTICE, to_link=link_spy)[0][
        proto.K_BODY
    ]
    assert private_body == "members in secret: (none)"
    assert missing_body == "members in nosuch: (none)"
    # Same response shape (only the room token differs).
    assert private_body.replace("secret", "X") == missing_body.replace("nosuch", "X")


def test_oracle_ban_list_requires_room_op():
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_spy, sess_spy = add_session(server, b"\xbb" * 16, nick="spy")
    join(server, link_op, sess_op, "lobby")
    join(server, link_spy, sess_spy, "lobby")
    banned = b"\xcc" * 16
    server.rooms.ensure_state("lobby")["bans"].add(banned)

    spy_out = msg(server, link_spy, sess_spy, "lobby", "/ban lobby list")
    assert envs_of_type(spy_out, proto.T_ERROR, to_link=link_spy)
    assert not any(
        banned.hex() in (env.get(proto.K_BODY) or "")
        for env in envs_of_type(spy_out, proto.T_NOTICE, to_link=link_spy)
    )

    op_out = msg(server, link_op, sess_op, "lobby", "/ban lobby list")
    notices = envs_of_type(op_out, proto.T_NOTICE, to_link=link_op)
    assert notices
    assert banned.hex() in notices[0][proto.K_BODY]


def test_oracle_unidentified_join_denied_for_keyed_room():
    server = make_server()
    server.register_room("vault", key="secret")
    link = FakeLink(FakeIdentity(b"\xdd" * 16))
    sess = _Session()
    sess.peer = None
    sess.nick = "ghost"
    sess.welcomed = True
    server._sessions[link] = sess
    out = join(server, link, sess, "vault", key="secret")
    assert any(
        e.get(proto.K_BODY) == "not identified"
        for e in envs_of_type(out, proto.T_ERROR)
    )
    assert "vault" not in sess.rooms


def test_oracle_join_strips_key_whitespace():
    server = make_server()
    server.register_room("vault", key="secret")
    link, sess = add_session(server, b"\xdd" * 16, nick="dee")
    out = join(server, link, sess, "vault", key="  secret  ")
    assert envs_of_type(out, proto.T_JOINED, to_link=link)
    assert "vault" in sess.rooms


def test_oracle_invite_only_link_drop_allows_rejoin():
    """After +i invite is consumed, link drop must still allow auto-rejoin.

    Intentional PART still requires a fresh invite (see
    test_oracle_invite_consumed_after_join).
    """
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_guest, sess_guest = add_session(server, b"\xbb" * 16, nick="guest")
    server.register_room("club", invite_only=True, founder=sess_op.peer)
    join(server, link_op, sess_op, "club")
    server.rooms.add_invite("club", sess_guest.peer, ttl_s=60)
    first = join(server, link_guest, sess_guest, "club")
    assert envs_of_type(first, proto.T_JOINED, to_link=link_guest)
    assert not server.rooms.is_invited("club", sess_guest.peer)

    server._on_close(link_guest)
    assert server.rooms.is_invited("club", sess_guest.peer)

    link_guest2, sess_guest2 = add_session(server, b"\xbb" * 16, nick="guest")
    second = join(server, link_guest2, sess_guest2, "club")
    assert envs_of_type(second, proto.T_JOINED, to_link=link_guest2)
    assert not server.rooms.is_invited("club", sess_guest.peer)


def test_oracle_invite_only_part_still_requires_fresh_invite():
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_guest, sess_guest = add_session(server, b"\xbb" * 16, nick="guest")
    server.register_room("club", invite_only=True, founder=sess_op.peer)
    join(server, link_op, sess_op, "club")
    server.rooms.add_invite("club", sess_guest.peer, ttl_s=60)
    join(server, link_guest, sess_guest, "club")
    part(server, link_guest, sess_guest, "club")
    assert not server.rooms.is_invited("club", sess_guest.peer)
    denied = join(server, link_guest, sess_guest, "club")
    assert any(
        e.get(proto.K_BODY) == "invite-only (+i)"
        for e in envs_of_type(denied, proto.T_ERROR)
    )


def test_oracle_invite_consumed_after_join():
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_guest, sess_guest = add_session(server, b"\xbb" * 16, nick="guest")
    server.register_room("club", invite_only=True, founder=sess_op.peer)
    server.rooms.add_invite("club", sess_guest.peer, ttl_s=60)
    first = join(server, link_guest, sess_guest, "club")
    assert envs_of_type(first, proto.T_JOINED, to_link=link_guest)
    assert not server.rooms.is_invited("club", sess_guest.peer)

    part(server, link_guest, sess_guest, "club")
    second = join(server, link_guest, sess_guest, "club")
    assert any(
        e.get(proto.K_BODY) == "invite-only (+i)"
        for e in envs_of_type(second, proto.T_ERROR)
    )


def test_oracle_hub_rejects_oversized_room_key():
    server = make_server()
    with pytest.raises(ValueError):
        server.set_room_key("vault", "x" * 300)


def test_property_bad_key_detector_ignores_mode_hints():
    assert RRCManager.is_bad_key_error("bad key (+k)") is True
    assert RRCManager.is_bad_key_error("ERROR: Bad Key (+K)") is True
    assert RRCManager.is_bad_key_error("failed: enable +k first") is False
    assert RRCManager.is_bad_key_error("invite-only (+i)") is False
    assert RRCManager.is_bad_key_error("+k") is False


def test_oracle_rooms_toml_dotted_and_unicode_roundtrip(tmp_path):
    path = str(tmp_path / "rooms.toml")
    founder = b"\x11" * 16
    registry = {
        "a.b": {
            "founder": founder,
            "registered": True,
            "topic": "dotted",
            "moderated": False,
            "invite_only": True,
            "topic_ops_only": False,
            "no_outside_msgs": True,
            "private": False,
            "key": "s3cret",
            "ops": {founder},
            "voiced": set(),
            "bans": set(),
            "invited": {},
            "last_used_ts": 123.0,
        },
        "café": {
            "founder": founder,
            "registered": True,
            "topic": "unicode",
            "moderated": True,
            "invite_only": False,
            "topic_ops_only": True,
            "no_outside_msgs": False,
            "private": True,
            "key": None,
            "ops": {founder},
            "voiced": set(),
            "bans": set(),
            "invited": {},
            "last_used_ts": 456.0,
        },
    }
    dump_rooms_registry(path, registry)
    loaded = load_rooms_registry(path)
    assert "a.b" in loaded
    assert loaded["a.b"]["key"] == "s3cret"
    assert loaded["a.b"]["invite_only"] is True
    assert loaded["a.b"]["no_outside_msgs"] is True
    assert "café" in loaded
    assert loaded["café"]["moderated"] is True
    assert loaded["café"]["private"] is True
    assert loaded["café"]["topic"] == "unicode"


def test_oracle_invite_ttl_boundary_denies_join():
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_guest, sess_guest = add_session(server, b"\xbb" * 16, nick="guest")
    server.register_room("club", invite_only=True, founder=sess_op.peer)
    server.rooms.add_invite("club", sess_guest.peer, ttl_s=0.05)
    time.sleep(0.08)
    out = join(server, link_guest, sess_guest, "club")
    assert any(
        e.get(proto.K_BODY) == "invite-only (+i)"
        for e in envs_of_type(out, proto.T_ERROR)
    )
    assert "club" not in sess_guest.rooms


def test_oracle_double_join_is_idempotent_for_peers():
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_b, sess_b = add_session(server, b"\xbb" * 16, nick="bob")
    join(server, link_a, sess_a, "lobby")
    join(server, link_b, sess_b, "lobby")
    out = join(server, link_b, sess_b, "lobby")
    fanouts = [
        env
        for lnk, env in out
        if lnk is link_a and env.get(proto.K_T) == proto.T_JOINED
    ]
    assert fanouts == [], "re-JOIN must not re-announce JOINED to peers"


@given(
    room=st.from_regex(r"[a-z0-9_-]{1,16}", fullmatch=True),
    key=st.one_of(st.none(), st.from_regex(r"[a-zA-Z0-9_-]{1,24}", fullmatch=True)),
)
@settings(max_examples=40, deadline=None)
def test_property_rooms_toml_simple_names_roundtrip(tmp_path_factory, room, key):
    path = str(tmp_path_factory.mktemp("rrc") / "rooms.toml")
    name = room.strip().lower()
    founder = b"\x33" * 16
    key_n = key if isinstance(key, str) and key else None
    registry = {
        name: {
            "founder": founder,
            "registered": True,
            "topic": None,
            "moderated": False,
            "invite_only": False,
            "topic_ops_only": False,
            "no_outside_msgs": False,
            "private": False,
            "key": key_n,
            "ops": {founder},
            "voiced": set(),
            "bans": set(),
            "invited": {},
            "last_used_ts": 1.0,
        },
    }
    dump_rooms_registry(path, registry)
    loaded = load_rooms_registry(path)
    assert name in loaded
    assert loaded[name]["key"] == registry[name]["key"]
    assert loaded[name]["registered"] is True


@given(
    wrong=st.text(min_size=1, max_size=24).filter(
        lambda s: s.strip() not in ("", "ok"),
    ),
)
@settings(max_examples=30, deadline=None)
def test_property_keyed_join_rejects_non_matching_keys(wrong):
    server = make_server()
    server.register_room("vault", key="ok")
    link, sess = add_session(server, os.urandom(16), nick="x")
    provided = wrong.strip()
    if provided == "ok":
        return
    out = join(server, link, sess, "vault", key=provided)
    assert any(
        e.get(proto.K_BODY) == "bad key (+k)" for e in envs_of_type(out, proto.T_ERROR)
    )
    assert "vault" not in sess.rooms
    assert server.rooms.ensure_state("vault").get("founder") is None


def _oracle_available_rooms_diff(previous, next_rooms):
    """Independent oracle for /list snapshot replace semantics."""
    prev = previous if isinstance(previous, dict) else {}
    nxt = next_rooms if isinstance(next_rooms, dict) else {}
    added = sorted(k for k in nxt if k not in prev)
    removed = sorted(k for k in prev if k not in nxt)
    updated = sorted(
        k for k in nxt if k in prev and (prev.get(k) or None) != (nxt.get(k) or None)
    )
    return added, removed, updated


@given(
    previous=st.dictionaries(
        st.from_regex(r"[a-z0-9_-]{1,12}", fullmatch=True),
        st.one_of(st.none(), st.from_regex(r"[A-Za-z0-9 _-]{0,24}", fullmatch=True)),
        max_size=8,
    ),
    next_rooms=st.dictionaries(
        st.from_regex(r"[a-z0-9_-]{1,12}", fullmatch=True),
        st.one_of(st.none(), st.from_regex(r"[A-Za-z0-9 _-]{0,24}", fullmatch=True)),
        max_size=8,
    ),
)
@settings(max_examples=60, deadline=None)
def test_oracle_list_notice_replaces_available_rooms(
    tmp_path_factory, previous, next_rooms
):
    """Hub /list notices replace available_rooms. Adds and removals both apply."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path_factory.mktemp("rrc-list")),
        get_nickname=(lambda: None),
    )
    hub = manager.add_hub(HUB_HASH)
    hub.available_rooms = dict(previous)
    hub._silent_list_pending = 1

    if not next_rooms:
        body = "No public rooms registered"
    else:
        lines = ["Registered public rooms"]
        for name, topic in sorted(next_rooms.items()):
            if topic:
                lines.append(f"{name} - {topic}")
            else:
                lines.append(name)
        body = "\n".join(lines)

    env = proto.make_envelope(proto.T_NOTICE, src=None, body=body)
    hub._on_packet(proto.encode(env))

    expected = {}
    for name, topic in next_rooms.items():
        if isinstance(topic, str):
            stripped = topic.strip()
            expected[name] = stripped or None
        else:
            expected[name] = None
    assert hub.available_rooms == expected
    assert hub.available_keyed_rooms == []
    added, removed, updated = _oracle_available_rooms_diff(previous, expected)
    for name in added:
        assert name in hub.available_rooms
        assert name not in previous
    for name in removed:
        assert name not in hub.available_rooms
        assert name in previous
    for name in updated:
        assert hub.available_rooms[name] != (previous.get(name) or None)


def test_oracle_unregister_preserves_live_key_modes_and_bans():
    """Slash /unregister must drop +r only. Live +k/+i/bans stay while members remain."""
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_bob, sess_bob = add_session(server, b"\xbb" * 16, nick="bob")
    banned = b"\xcc" * 16
    server.register_room(
        "vault",
        key="secret",
        invite_only=True,
        founder=sess_op.peer,
    )
    join(server, link_op, sess_op, "vault", key="secret")
    server.rooms.add_invite("vault", sess_bob.peer, ttl_s=60)
    join(server, link_bob, sess_bob, "vault")
    server.rooms.ensure_state("vault")["bans"].add(banned)

    out = msg(server, link_op, sess_op, "vault", "/unregister vault")
    assert envs_of_type(out, proto.T_ERROR, to_link=link_op) == []
    st = server.rooms.get_state("vault")
    assert st is not None
    assert st.get("registered") is False
    assert st.get("key") == "secret"
    assert st.get("invite_only") is True
    assert banned in (st.get("bans") or set())
    assert sess_op.peer in (st.get("ops") or set())

    link_eve, sess_eve = add_session(server, b"\xee" * 16, nick="eve")
    denied = join(server, link_eve, sess_eve, "vault")
    assert any(
        e.get(proto.K_BODY) == "invite-only (+i)"
        for e in envs_of_type(denied, proto.T_ERROR)
    )
    assert "vault" not in sess_eve.rooms


def test_oracle_rejoin_at_room_cap_succeeds():
    """Re-JOIN of a room you already occupy must not hit the session room cap."""
    server = make_server()
    server.max_rooms_per_session = 1
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    first = join(server, link, sess, "lobby")
    assert envs_of_type(first, proto.T_JOINED, to_link=link)
    out = join(server, link, sess, "lobby")
    assert not any(
        "too many" in str(e.get(proto.K_BODY) or "").lower()
        for e in envs_of_type(out, proto.T_ERROR)
    )
    assert envs_of_type(out, proto.T_JOINED, to_link=link)
    assert "lobby" in sess.rooms


def test_oracle_mode_and_ban_unknown_room_do_not_create_ghost_state():
    """Failed ACL commands must not persist rooms.toml-style ghost state."""
    server = make_server()
    link, sess = add_session(server, b"\xaa" * 16, nick="alice")
    join(server, link, sess, "lobby")
    msg(server, link, sess, "lobby", "/mode ghostroom +m")
    assert server.rooms.get_state("ghostroom") is None
    msg(server, link, sess, "lobby", "/ban ghostroom list")
    assert server.rooms.get_state("ghostroom") is None
    msg(server, link, sess, "lobby", "/kick ghostroom bob")
    assert server.rooms.get_state("ghostroom") is None


def test_oracle_non_founder_cannot_register_unregistered_room():
    """Only the founder or a room op may /register, even before +r is set."""
    server = make_server()
    link_a, sess_a = add_session(server, b"\xaa" * 16, nick="alice")
    link_b, sess_b = add_session(server, b"\xbb" * 16, nick="bob")
    join(server, link_a, sess_a, "lobby")
    join(server, link_b, sess_b, "lobby")
    assert server.rooms.get_state("lobby")["founder"] == sess_a.peer
    denied = msg(server, link_b, sess_b, "lobby", "/register lobby")
    assert envs_of_type(denied, proto.T_ERROR, to_link=link_b)
    assert server.rooms.get_state("lobby")["registered"] is False
    ok = msg(server, link_a, sess_a, "lobby", "/register lobby")
    assert envs_of_type(ok, proto.T_ERROR, to_link=link_a) == []
    assert server.rooms.get_state("lobby")["registered"] is True


def test_oracle_outside_msg_does_not_add_client_member(tmp_path):
    """Without +n, hub MSG from a non-member must not pollute the client member list."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    own = b"\x11" * 16
    member = b"\xaa" * 16
    outsider = b"\xee" * 16
    hub.rooms.add("lobby")
    hub.members["lobby"] = {own, member}
    hub._handle_msg(
        proto.make_envelope(
            proto.T_MSG,
            src=outsider,
            room="lobby",
            nick="eve",
            body="from outside",
        ),
    )
    assert outsider not in hub.members.get("lobby", set())
    assert hub.members["lobby"] == {own, member}
    assert hub.nicks.get(outsider) == "eve"


def test_oracle_rejoin_does_not_consume_fresh_invite():
    """Re-JOIN while already a member must not burn a newly issued invite."""
    server = make_server()
    link_op, sess_op = add_session(server, b"\xaa" * 16, nick="op")
    link_guest, sess_guest = add_session(server, b"\xbb" * 16, nick="guest")
    server.register_room("club", invite_only=True, founder=sess_op.peer)
    join(server, link_op, sess_op, "club")
    server.rooms.add_invite("club", sess_guest.peer, ttl_s=60)
    join(server, link_guest, sess_guest, "club")
    assert not server.rooms.is_invited("club", sess_guest.peer)
    server.rooms.add_invite("club", sess_guest.peer, ttl_s=60)
    assert server.rooms.is_invited("club", sess_guest.peer)
    join(server, link_guest, sess_guest, "club")
    assert server.rooms.is_invited("club", sess_guest.peer)
    part(server, link_guest, sess_guest, "club")
    again = join(server, link_guest, sess_guest, "club")
    assert envs_of_type(again, proto.T_JOINED, to_link=link_guest)


def test_oracle_disconnected_send_does_not_keep_local_history(tmp_path):
    """A failed send must not leave a chat line that never left the node."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    with pytest.raises(RuntimeError, match="not connected"):
        hub.send_message("lobby", "ghost")
    assert hub.messages.get("lobby", []) == []
    with pytest.raises(RuntimeError, match="not connected"):
        hub.send_action("lobby", "waves")
    assert hub.messages.get("lobby", []) == []
    with pytest.raises(RuntimeError, match="not connected"):
        hub.send_command("/who lobby", room="lobby")
    assert hub.messages.get("lobby", []) == []


def test_oracle_disconnected_join_does_not_keep_pending(tmp_path):
    """A failed JOIN must not treat a later peer JOINED as our own join."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    with pytest.raises(RuntimeError, match="not connected"):
        hub.join_room("lobby")
    assert "lobby" not in hub._pending_joins
    hub._handle_joined(
        proto.make_envelope(
            proto.T_JOINED,
            src=HUB_HASH,
            room="lobby",
            body=[b"\xaa" * 16],
            nick="alice",
        ),
    )
    texts = [m.text for m in hub.messages.get("lobby", [])]
    assert not any(t.startswith("You joined") for t in texts)
    assert any("joined" in t for t in texts)


def test_oracle_welcome_timeout_reconnects_when_teardown_skips_closed(tmp_path):
    """WELCOME timeout must reconnect even if link.teardown never fires closed."""
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    hub = manager.add_hub(HUB_HASH, name="Client")
    hub.auto_reconnect = True
    hub._manual_disconnect = False
    hub.welcomed = False
    hub.status = RRCHub.STATUS_CONNECTING

    class DeadLink:
        status = 2

        def teardown(self):
            return None

    hub.link = DeadLink()
    try:
        hub._fail_welcome_timeout()
        assert hub.link is None
        assert hub._reconnect_timer is not None
    finally:
        if hub._reconnect_timer is not None:
            hub._reconnect_timer.cancel()
            hub._reconnect_timer = None
