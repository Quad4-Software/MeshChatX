# SPDX-License-Identifier: 0BSD

"""Reticulum Relay Chat hub hosting.

Provides :class:`RRCHubServer`, a self-contained RRC hub that listens on a
Reticulum destination and relays messages between connected clients, and
:class:`RRCServerManager`, which lets a node host several independent hubs and
manage their public rooms. The wire behaviour mirrors the reference rrcd hub so
standard RRC clients (including the MeshChatX client) can connect.
"""

import contextlib
import os
import threading
import time
from collections import deque

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.hub_commands import HubCommandHandler
from meshchatx.src.backend.rrc.hub_policy import HubPolicy
from meshchatx.src.backend.rrc.identity_util import parse_identity_hash
from meshchatx.src.backend.rrc.room_registry import RoomRegistry
from meshchatx.src.backend.rrc.rooms_toml import RoomsTomlStore

SERVER_DIR_NAME = "rrc_server"
MESSAGE_LOG_CAP = 5000
STORE_FILENAME = "hubs"
HUB_CONFIG_FILENAME = "hub.toml"
ROOMS_FILENAME = "rooms.toml"


class _LoopbackEndpoint:
    """In-process link bridging a local client hub to a hosted hub server.

    Reticulum does not loop packets back to destinations hosted within the same
    instance, so connecting to a locally hosted hub goes through this direct
    bridge instead of the mesh. It exposes just enough of the
    :class:`RNS.Link` surface for both sides to treat it like a link.
    """

    def __init__(self, client_hub, server):
        self.status = RNS.Link.ACTIVE
        self._client = client_hub
        self._server = server
        self._closed = False

    def get_remote_identity(self):
        return self._client.manager.identity

    def from_client(self, payload):
        if not self._closed:
            self._server._on_packet(self, payload)

    def from_server(self, payload):
        if not self._closed:
            self._client._on_packet(payload)

    def teardown(self):
        if self._closed:
            return
        self._closed = True
        self.status = RNS.Link.CLOSED
        with contextlib.suppress(Exception):
            self._server._detach_loopback(self)
        with contextlib.suppress(Exception):
            self._client._on_closed(self)


class _Session:
    """Per-link client session state."""

    def __init__(self):
        self.welcomed = False
        self.peer = None
        self.nick = None
        self.rooms = set()
        self.tokens = float(proto.DEFAULT_RATE_PER_MINUTE)
        self.last_refill = time.monotonic()


class RRCHubServer:
    """A single hosted RRC hub with its own Reticulum identity and rooms."""

    def __init__(
        self,
        manager,
        identity,
        name=None,
        greeting=None,
        announce=True,
        enabled=True,
    ):
        self.manager = manager
        self.identity = identity
        self.hub_id = identity.hash.hex()
        self.name = name or ("Hub " + identity.hash.hex()[:8])
        self.greeting = greeting
        self.announce = announce
        self.enabled = enabled

        self.max_nick_bytes = proto.DEFAULT_MAX_NICK_BYTES
        self.max_room_name_bytes = proto.DEFAULT_MAX_ROOM_BYTES
        self.max_msg_body_bytes = proto.DEFAULT_MAX_MSG_BYTES
        self.max_rooms_per_session = proto.DEFAULT_MAX_ROOMS
        self.rate_limit_msgs_per_minute = proto.DEFAULT_RATE_PER_MINUTE

        self.destination = None
        self.running = False
        self._started_at = None

        self._lock = threading.RLock()
        self._sessions = {}
        self._room_members = {}
        self._hub_dir = None
        self.policy = HubPolicy()
        self.rooms = RoomRegistry(self, None)
        self._commands = HubCommandHandler()
        self._message_log = deque(maxlen=MESSAGE_LOG_CAP)

    @property
    def dest_hash(self):
        if self.destination is not None:
            return self.destination.hash
        return None

    def _log(self, msg, level=None):
        if level is None:
            level = RNS.LOG_INFO
        RNS.log("[RRC hub " + self.name + "] " + msg, level)

    def start(self):
        with self._lock:
            if self.running:
                return
            app_name, aspects = RNS.Destination.app_and_aspects_from_name(
                proto.DEFAULT_DEST_NAME,
            )
            self.destination = RNS.Destination(
                self.identity,
                RNS.Destination.IN,
                RNS.Destination.SINGLE,
                app_name,
                *aspects,
            )
            self.destination.set_link_established_callback(self._on_link)
            self.running = True
            self._started_at = time.time()
        if self.announce:
            self.announce_now()
        self._log("hub started at " + self.dest_hash.hex())

    def announce_now(self):
        if self.destination is None:
            return
        with contextlib.suppress(Exception):
            self.destination.announce(
                app_data=proto.encode({"proto": "rrc", "v": 1, "hub": self.name}),
            )

    def stop(self):
        with self._lock:
            links = list(self._sessions.keys())
            self._sessions.clear()
            self._room_members.clear()
            dest = self.destination
            self.destination = None
            self.running = False
            self._started_at = None
        for link in links:
            with contextlib.suppress(Exception):
                link.teardown()
        if dest is not None:
            with contextlib.suppress(Exception):
                RNS.Transport.deregister_destination(dest)

    def _norm_room(self, room):
        r = proto.normalize_room(room)
        if len(r.encode("utf-8", errors="replace")) > self.max_room_name_bytes:
            msg = "room name too long"
            raise ValueError(msg)
        return r

    def _on_link(self, link):
        with self._lock:
            self._sessions[link] = _Session()
        link.set_packet_callback(lambda data, pkt: self._on_packet(link, data))
        link.set_link_closed_callback(self._on_close)
        link.set_remote_identified_callback(self._on_remote_identified)

    def configure_storage(self, hub_dir, trusted=None, banned=None):
        """Attach per-hub storage (hub.toml, rooms.toml) under hub_dir."""
        self._hub_dir = hub_dir
        os.makedirs(hub_dir, exist_ok=True)
        policy_path = os.path.join(hub_dir, HUB_CONFIG_FILENAME)
        rooms_path = os.path.join(hub_dir, ROOMS_FILENAME)
        self.policy = HubPolicy(policy_path)
        if trusted is not None:
            self.policy.apply_config(trusted_list=trusted)
        if banned is not None:
            self.policy.apply_config(banned_list=banned)
        if trusted is not None or banned is not None:
            self.policy.save()
        self.rooms = RoomRegistry(self, RoomsTomlStore(rooms_path))

    def _disconnect_banned(self, peer_hash, outgoing, message):
        with self._lock:
            targets = [
                (lnk, sess)
                for lnk, sess in self._sessions.items()
                if isinstance(sess.peer, (bytes, bytearray))
                and bytes(sess.peer) == bytes(peer_hash)
            ]
        for lnk, sess in targets:
            self._queue_error(outgoing, lnk, message)
            with contextlib.suppress(Exception):
                if hasattr(lnk, "teardown"):
                    lnk.teardown()

    def _on_remote_identified(self, link, identity):
        if identity is None:
            return
        with self._lock:
            sess = self._sessions.get(link)
            if sess is not None:
                sess.peer = identity.hash
        if identity is not None and self.policy.is_banned(identity.hash):
            self._log(
                "Disconnecting banned peer " + identity.hash.hex()[:12],
                RNS.LOG_WARNING,
            )
            outgoing = []
            self._disconnect_banned(identity.hash, outgoing, "banned")
            for out_link, payload in outgoing:
                self._send_payload(out_link, payload)
            with contextlib.suppress(Exception):
                link.teardown()

    def _on_close(self, link):
        parted = []
        with self._lock:
            sess = self._sessions.pop(link, None)
            if sess is None:
                return
            for room in list(sess.rooms):
                members = self._room_members.get(room)
                if members is None:
                    continue
                members.discard(link)
                remaining = list(members)
                reg = self.rooms.get_state(room)
                if not members and (reg is None or not reg.get("registered")):
                    self._room_members.pop(room, None)
                if remaining and sess.peer is not None:
                    parted.append((room, sess.peer, sess.nick, remaining))
        for room, peer, nick, remaining in parted:
            env = proto.make_envelope(
                proto.T_PARTED,
                src=self.identity.hash,
                room=room,
                body=[peer],
                nick=nick,
            )
            payload = proto.encode(env)
            for member in remaining:
                self._send_payload(member, payload)
        self.manager._notify_change(self)

    def _refill_and_take(self, sess, cost=1.0):
        now = time.monotonic()
        per_min = float(max(1, int(self.rate_limit_msgs_per_minute)))
        elapsed = max(0.0, now - sess.last_refill)
        sess.tokens = min(per_min, sess.tokens + elapsed * (per_min / 60.0))
        sess.last_refill = now
        if sess.tokens < cost:
            return False
        sess.tokens -= cost
        return True

    def _send_payload(self, link, payload):
        if isinstance(link, _LoopbackEndpoint):
            link.from_server(payload)
            return
        with contextlib.suppress(Exception):
            RNS.Packet(link, payload).send()

    def _attach_loopback(self, link, client_identity):
        with self._lock:
            sess = _Session()
            sess.peer = client_identity.hash if client_identity is not None else None
            self._sessions[link] = sess
        self.manager._notify_change(self)

    def _detach_loopback(self, link):
        self._on_close(link)

    def _on_packet(self, link, data):
        try:
            env = proto.decode(data)
        except Exception:
            return
        if not isinstance(env, dict):
            return
        with self._lock:
            sess = self._sessions.get(link)
            if sess is None:
                return
            if sess.peer is None:
                ri = link.get_remote_identity()
                if ri is None:
                    return
                sess.peer = ri.hash
            outgoing = []
            self._route(link, sess, env, outgoing)
        for out_link, payload in outgoing:
            self._send_payload(out_link, payload)

    def _route(self, link, sess, env, outgoing):
        t = env.get(proto.K_T)
        if t == proto.T_PONG:
            return
        if t == proto.T_PING:
            outgoing.append(
                (
                    link,
                    proto.encode(
                        proto.make_envelope(
                            proto.T_PONG,
                            src=self.identity.hash,
                            body=env.get(proto.K_BODY),
                        ),
                    ),
                )
            )
            return
        if not sess.welcomed:
            self._handle_hello(link, sess, env, outgoing)
            return
        if not self._refill_and_take(sess):
            outgoing.append(
                (
                    link,
                    proto.encode(
                        proto.make_envelope(
                            proto.T_ERROR,
                            src=self.identity.hash,
                            body="rate limited",
                        ),
                    ),
                )
            )
            return
        if t == proto.T_HELLO:
            self._handle_hello(link, sess, env, outgoing)
        elif t == proto.T_JOIN:
            self._handle_join(link, sess, env, outgoing)
        elif t == proto.T_PART:
            self._handle_part(link, sess, env, outgoing)
        elif t in (proto.T_MSG, proto.T_ACTION, proto.T_NOTICE):
            self._handle_message(link, sess, env, outgoing)

    def _handle_hello(self, link, sess, env, outgoing):
        nick = proto.normalize_nick(env.get(proto.K_NICK), self.max_nick_bytes)
        if nick is not None:
            sess.nick = nick
        sess.welcomed = True
        caps = {proto.CAP_ACTION: True}
        limits = {
            proto.L_MAX_NICK_BYTES: self.max_nick_bytes,
            proto.L_MAX_ROOM_NAME_BYTES: self.max_room_name_bytes,
            proto.L_MAX_MSG_BODY_BYTES: self.max_msg_body_bytes,
            proto.L_MAX_ROOMS_PER_SESSION: self.max_rooms_per_session,
            proto.L_RATE_LIMIT_MSGS_PER_MINUTE: self.rate_limit_msgs_per_minute,
        }
        body = {
            proto.B_WELCOME_HUB: self.name,
            proto.B_WELCOME_VER: proto.HELLO_CLIENT_VERSION,
            proto.B_WELCOME_CAPS: caps,
            proto.B_WELCOME_LIMITS: limits,
        }
        outgoing.append(
            (
                link,
                proto.encode(
                    proto.make_envelope(
                        proto.T_WELCOME, src=self.identity.hash, body=body
                    ),
                ),
            )
        )
        if self.greeting:
            outgoing.append(
                (
                    link,
                    proto.encode(
                        proto.make_envelope(
                            proto.T_NOTICE,
                            src=self.identity.hash,
                            body=self.greeting,
                        ),
                    ),
                )
            )

    def _room_member_hashes(self, room):
        hashes = []
        for member in self._room_members.get(room, set()):
            s = self._sessions.get(member)
            if s is not None and isinstance(s.peer, (bytes, bytearray)):
                hashes.append(bytes(s.peer))
        return hashes

    def _handle_join(self, link, sess, env, outgoing):
        room = env.get(proto.K_ROOM)
        if not isinstance(room, str) or not room:
            self._queue_error(outgoing, link, "JOIN requires room name")
            return
        if len(sess.rooms) >= self.max_rooms_per_session:
            self._queue_error(outgoing, link, "too many rooms")
            return
        try:
            r = self._norm_room(room)
        except ValueError as e:
            self._queue_error(outgoing, link, str(e))
            return

        peer = sess.peer if isinstance(sess.peer, (bytes, bytearray)) else None
        join_body = env.get(proto.K_BODY)
        if peer is not None and self.rooms.is_room_banned(r, peer):
            self._queue_error(outgoing, link, "banned from room", room=r)
            return

        st = self.rooms.ensure_state(r, founder=peer)
        if bool(st.get("invite_only")):
            if (
                peer is not None
                and not self.rooms.is_room_op(r, peer)
                and not self.rooms.is_invited(r, peer)
            ):
                self._queue_error(outgoing, link, "invite-only (+i)", room=r)
                return

        key = st.get("key")
        if isinstance(key, str) and key:
            if (
                peer is not None
                and not self.rooms.is_room_op(r, peer)
                and not self.rooms.is_invited(r, peer)
            ):
                provided = join_body if isinstance(join_body, str) else None
                if provided != key:
                    self._queue_error(outgoing, link, "bad key (+k)", room=r)
                    return

        if not self._room_members.get(r):
            self.rooms.ensure_state(r, founder=peer)

        members = self._room_members.setdefault(r, set())
        existing = [m for m in members if m != link]
        members.add(link)
        sess.rooms.add(r)

        if existing:
            fanout = proto.encode(
                proto.make_envelope(
                    proto.T_JOINED,
                    src=self.identity.hash,
                    room=r,
                    body=[sess.peer] if sess.peer is not None else None,
                    nick=sess.nick,
                ),
            )
            for member in existing:
                outgoing.append((member, fanout))

        outgoing.append(
            (
                link,
                proto.encode(
                    proto.make_envelope(
                        proto.T_JOINED,
                        src=self.identity.hash,
                        room=r,
                        body=self._room_member_hashes(r),
                    ),
                ),
            )
        )

        st = self.rooms.ensure_state(r)
        topic = st.get("topic")
        reg_txt = "registered" if st.get("registered") else "unregistered"
        modes = self.rooms.get_mode_string(r)
        self._queue_notice(
            outgoing,
            link,
            r,
            "room "
            + r
            + ": "
            + reg_txt
            + "; topic="
            + (topic or "(none)")
            + "; modes="
            + modes,
        )
        self.rooms.touch_room(r)
        self.manager._notify_change(self)

    def _handle_part(self, link, sess, env, outgoing):
        room = env.get(proto.K_ROOM)
        if not isinstance(room, str) or not room:
            self._queue_error(outgoing, link, "PART requires room name")
            return
        try:
            r = self._norm_room(room)
        except ValueError as e:
            self._queue_error(outgoing, link, str(e))
            return

        sess.rooms.discard(r)
        members = self._room_members.get(r)
        remaining = []
        if members is not None:
            members.discard(link)
            remaining = list(members)
            reg = self.rooms.get_state(r)
            if not members and (reg is None or not reg.get("registered")):
                self._room_members.pop(r, None)

        if remaining and sess.peer is not None:
            fanout = proto.encode(
                proto.make_envelope(
                    proto.T_PARTED,
                    src=self.identity.hash,
                    room=r,
                    body=[sess.peer],
                    nick=sess.nick,
                ),
            )
            for member in remaining:
                outgoing.append((member, fanout))

        outgoing.append(
            (
                link,
                proto.encode(
                    proto.make_envelope(
                        proto.T_PARTED,
                        src=self.identity.hash,
                        room=r,
                        body=[sess.peer] if sess.peer is not None else None,
                    ),
                ),
            )
        )
        self.manager._notify_change(self)

    def _handle_message(self, link, sess, env, outgoing):
        t = env.get(proto.K_T)
        room = env.get(proto.K_ROOM)
        body = env.get(proto.K_BODY)

        if t in (proto.T_MSG, proto.T_NOTICE) and isinstance(body, str):
            if body.strip().startswith("/"):
                if self._commands.handle(self, link, sess, room, body, outgoing):
                    return
                self._queue_error(outgoing, link, "unrecognized command", room=room)
                return

        if not isinstance(room, str) or not room:
            self._queue_error(outgoing, link, "message requires room name")
            return
        if (
            isinstance(body, str)
            and len(body.encode("utf-8", errors="replace")) > self.max_msg_body_bytes
        ):
            self._queue_error(outgoing, link, "message too large")
            return
        try:
            r = self._norm_room(room)
        except ValueError as e:
            self._queue_error(outgoing, link, str(e))
            return

        peer = sess.peer if isinstance(sess.peer, (bytes, bytearray)) else None

        if r not in sess.rooms:
            st_check = self.rooms.get_state(r)
            if st_check is None and not self._room_members.get(r):
                self._queue_error(outgoing, link, "no such room", room=r)
                return
            if st_check is not None and bool(st_check.get("no_outside_msgs")):
                self._queue_error(outgoing, link, "no outside messages (+n)", room=r)
                return

        if peer is not None and self.rooms.is_room_banned(r, peer):
            self._queue_error(outgoing, link, "banned from room", room=r)
            return

        if self.rooms.is_room_moderated(r) and not self.rooms.is_room_voiced(r, peer):
            self._queue_error(outgoing, link, "room is moderated (+m)", room=r)
            return

        members = self._room_members.get(r)
        if not members:
            self._queue_error(outgoing, link, "no such room", room=r)
            return

        env[proto.K_SRC] = (
            bytes(sess.peer) if isinstance(sess.peer, (bytes, bytearray)) else sess.peer
        )
        env[proto.K_ROOM] = r
        incoming_nick = proto.normalize_nick(env.get(proto.K_NICK), self.max_nick_bytes)
        if incoming_nick is not None:
            sess.nick = incoming_nick
            env[proto.K_NICK] = incoming_nick
        elif sess.nick:
            env[proto.K_NICK] = sess.nick
        else:
            env.pop(proto.K_NICK, None)

        payload = proto.encode(env)
        self._record_message_log(r, sess, env)
        for member in list(members):
            outgoing.append((member, payload))

    def _record_message_log(self, room, sess, env):
        t = env.get(proto.K_T)
        if t not in (proto.T_MSG, proto.T_ACTION):
            return
        body = env.get(proto.K_BODY)
        if not isinstance(body, str) or not body.strip():
            return
        if body.strip().startswith("/"):
            return
        peer = sess.peer
        if not isinstance(peer, (bytes, bytearray)):
            return
        nick = sess.nick if isinstance(sess.nick, str) else None
        if nick is None:
            incoming = proto.normalize_nick(env.get(proto.K_NICK), self.max_nick_bytes)
            if incoming is not None:
                nick = incoming
        text = body
        if len(text.encode("utf-8", errors="replace")) > 500:
            text = text[:500] + "..."
        with self._lock:
            self._message_log.append(
                {
                    "ts": proto.now_ms(),
                    "room": room,
                    "peer": bytes(peer).hex(),
                    "nick": nick,
                    "kind": "action" if t == proto.T_ACTION else "msg",
                    "text": text,
                },
            )

    def _flush_outgoing(self, outgoing):
        for out_link, payload in outgoing:
            self._send_payload(out_link, payload)

    def _queue_notice(self, outgoing, link, room, text):
        outgoing.append(
            (
                link,
                proto.encode(
                    proto.make_envelope(
                        proto.T_NOTICE,
                        src=self.identity.hash,
                        room=room,
                        body=text,
                    ),
                ),
            )
        )

    def _queue_error(self, outgoing, link, text, room=None):
        outgoing.append(
            (
                link,
                proto.encode(
                    proto.make_envelope(
                        proto.T_ERROR,
                        src=self.identity.hash,
                        room=room,
                        body=text,
                    ),
                ),
            )
        )

    def register_room(
        self,
        name,
        topic=None,
        private=False,
        moderated=False,
        invite_only=False,
        topic_ops_only=False,
        no_outside_msgs=False,
        key=None,
        founder=None,
    ):
        r = self._norm_room(name)
        with self._lock:
            self.rooms.register_room(
                r,
                topic=topic,
                private=private,
                moderated=moderated,
                invite_only=invite_only,
                topic_ops_only=topic_ops_only,
                no_outside_msgs=no_outside_msgs,
                key=key,
                founder=founder,
            )
            self._room_members.setdefault(r, set())
        return r

    def unregister_room(self, name):
        r = proto.normalize_room(name)
        with self._lock:
            self.rooms.unregister_room(r)
            members = self._room_members.get(r)
            if members is not None and not members:
                self._room_members.pop(r, None)
        return r

    def set_room_topic(self, name, topic):
        r = proto.normalize_room(name)
        st = self.rooms.ensure_state(r)
        st["topic"] = topic or None
        if st.get("registered"):
            self.rooms.persist(r)

    def client_count(self):
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.welcomed)

    def members_dict(self, room=None):
        """Return connected clients, optionally filtered to a single room."""
        with self._lock:
            out = []
            if room is not None:
                r = self._norm_room(room)
                links = list(self._room_members.get(r, set()))
                seen = set()
                for link in links:
                    sess = self._sessions.get(link)
                    if sess is None or not sess.welcomed:
                        continue
                    peer = sess.peer
                    if not isinstance(peer, (bytes, bytearray)):
                        continue
                    ph = bytes(peer)
                    if ph in seen:
                        continue
                    seen.add(ph)
                    out.append(self._member_entry(sess, ph))
            else:
                for sess in self._sessions.values():
                    if not sess.welcomed:
                        continue
                    peer = sess.peer
                    if not isinstance(peer, (bytes, bytearray)):
                        continue
                    out.append(self._member_entry(sess, bytes(peer)))
            out.sort(key=lambda m: m["name"].lower())
            return out

    def _member_entry(self, sess, peer_hash):
        nick = sess.nick if isinstance(sess.nick, str) and sess.nick else None
        return {
            "hash": peer_hash.hex(),
            "name": nick or peer_hash.hex()[:12],
            "nick": nick,
            "rooms": sorted(sess.rooms),
        }

    def rooms_activity(self):
        with self._lock:
            rooms_cfg = {}
            names = set(self.rooms._registry.keys()) | set(self._room_members.keys())
            for name in names:
                cfg = self.rooms.room_config_for_api(name)
                cfg["members"] = len(self._room_members.get(name, set()))
                cfg["message_count"] = 0
                cfg["last_activity_ts"] = None
                rooms_cfg[name] = cfg
            recent = []
            for entry in reversed(self._message_log):
                r = entry.get("room")
                if r in rooms_cfg:
                    rooms_cfg[r]["message_count"] += 1
                    ts = entry.get("ts")
                    if ts is not None and (
                        rooms_cfg[r]["last_activity_ts"] is None
                        or ts > rooms_cfg[r]["last_activity_ts"]
                    ):
                        rooms_cfg[r]["last_activity_ts"] = ts
                if len(recent) < 80:
                    recent.append(dict(entry))
            rooms = [rooms_cfg[n] for n in sorted(rooms_cfg.keys())]
            return {"rooms": rooms, "recent": list(reversed(recent))}

    def messages_for_peer(self, peer_hex, room=None, limit=200):
        peer = parse_identity_hash(peer_hex)
        if peer is None:
            msg = "invalid peer hash"
            raise ValueError(msg)
        ph = peer.hex()
        limit = max(1, min(int(limit) if limit is not None else 200, 500))
        room_n = None
        if isinstance(room, str) and room.strip():
            room_n = self._norm_room(room)
        out = []
        with self._lock:
            for entry in reversed(self._message_log):
                if entry.get("peer") != ph:
                    continue
                if room_n is not None and entry.get("room") != room_n:
                    continue
                out.append(dict(entry))
                if len(out) >= limit:
                    break
        out.reverse()
        return out

    def admin_kick_from_room(self, peer_hex, room):
        peer = parse_identity_hash(peer_hex)
        if peer is None:
            msg = "invalid peer hash"
            raise ValueError(msg)
        r = self._norm_room(room)
        outgoing = []
        with self._lock:
            target_link = None
            for link, sess in self._sessions.items():
                if (
                    isinstance(sess.peer, (bytes, bytearray))
                    and bytes(sess.peer) == peer
                    and r in sess.rooms
                ):
                    target_link = link
                    break
            if target_link is None:
                msg = "peer not in room"
                raise ValueError(msg)
            tsess = self._sessions[target_link]
            tsess.rooms.discard(r)
            members = self._room_members.get(r)
            if members is not None:
                members.discard(target_link)
        self._queue_error(outgoing, target_link, "kicked from " + r, room=r)
        self._flush_outgoing(outgoing)
        return True

    def admin_hub_ban(self, peer_hex):
        peer = parse_identity_hash(peer_hex)
        if peer is None:
            msg = "invalid peer hash"
            raise ValueError(msg)
        outgoing = []
        self.policy.add_ban(peer)
        self.policy.save()
        self._disconnect_banned(peer, outgoing, "banned (kline)")
        self._flush_outgoing(outgoing)
        return True

    def admin_room_ban(self, peer_hex, room):
        peer = parse_identity_hash(peer_hex)
        if peer is None:
            msg = "invalid peer hash"
            raise ValueError(msg)
        r = self._norm_room(room)
        outgoing = []
        with self._lock:
            st = self.rooms.ensure_state(r)
            bans = st.setdefault("bans", set())
            bans.add(peer)
            self.rooms.touch_room(r)
            self.rooms.persist(r)
            for member in list(self._room_members.get(r, set())):
                ms = self._sessions.get(member)
                if ms is not None and isinstance(ms.peer, (bytes, bytearray)):
                    if bytes(ms.peer) == peer:
                        ms.rooms.discard(r)
                        self._room_members[r].discard(member)
                        self._queue_error(
                            outgoing,
                            member,
                            "banned from " + r,
                            room=r,
                        )
        self._flush_outgoing(outgoing)
        return True

    def to_dict(self):
        """Return a JSON-serializable summary of this hub."""
        with self._lock:
            rooms = []
            names = set(self.rooms._registry.keys()) | set(self._room_members.keys())
            for name in sorted(names):
                cfg = self.rooms.room_config_for_api(name)
                cfg["members"] = len(self._room_members.get(name, set()))
                rooms.append(cfg)
            policy = self.policy.to_dict()
            uptime_seconds = 0
            if self.running and self._started_at is not None:
                uptime_seconds = max(0, int(time.time() - self._started_at))
            return {
                "id": self.hub_id,
                "name": self.name,
                "dest_hash": self.dest_hash.hex() if self.dest_hash else None,
                "enabled": self.enabled,
                "running": self.running,
                "uptime_seconds": uptime_seconds,
                "announce": self.announce,
                "greeting": self.greeting,
                "clients": sum(1 for s in self._sessions.values() if s.welcomed),
                "trusted_identities": policy["trusted_identities"],
                "banned_identities": policy["banned_identities"],
                "rooms": rooms,
            }

    def config_entry(self):
        with self._lock:
            rooms = []
            for name in sorted(self.rooms._registry.keys()):
                st = self.rooms._registry[name]
                rooms.append(
                    {
                        "name": name,
                        "topic": st.get("topic"),
                        "private": bool(st.get("private")),
                        "moderated": bool(st.get("moderated")),
                        "invite_only": bool(st.get("invite_only")),
                        "topic_ops_only": bool(st.get("topic_ops_only")),
                        "no_outside_msgs": bool(st.get("no_outside_msgs")),
                        "key": st.get("key"),
                    }
                )
            policy = self.policy.to_dict()
        return {
            "id": self.hub_id,
            "name": self.name,
            "enabled": self.enabled,
            "announce": self.announce,
            "greeting": self.greeting,
            "trusted_identities": policy["trusted_identities"],
            "banned_identities": policy["banned_identities"],
            "rooms": rooms,
        }


class RRCServerManager:
    """Hosts and persists multiple RRC hubs for a single node."""

    def __init__(self, storage_dir, on_change=None, owner_identity=None):
        self.storage_dir = storage_dir
        self._on_change = on_change
        self.owner_identity = (
            bytes(owner_identity)
            if isinstance(owner_identity, (bytes, bytearray))
            else None
        )
        self.hubs = []
        self._lock = threading.RLock()
        self._loaded = False
        self._save_lock = threading.Lock()

    def _owner_trusted_hex_list(self):
        if self.owner_identity is None:
            return None
        return [bytes(self.owner_identity).hex()]

    def set_change_callback(self, cb):
        self._on_change = cb

    def _notify_change(self, hub=None):
        with contextlib.suppress(Exception):
            if self._on_change is not None:
                self._on_change(hub)

    def _server_dir(self):
        return os.path.join(self.storage_dir, SERVER_DIR_NAME)

    def _store_path(self):
        return os.path.join(self._server_dir(), STORE_FILENAME)

    def _identity_path(self, hub_id):
        return os.path.join(self._server_dir(), hub_id + ".identity")

    def _hub_dir(self, hub_id):
        return os.path.join(self._server_dir(), hub_id)

    def find_hub(self, hub_id):
        with self._lock:
            for hub in self.hubs:
                if hub.hub_id == hub_id:
                    return hub
        return None

    def create_hub(self, name=None, greeting=None, announce=True, enabled=True):
        identity = RNS.Identity()
        os.makedirs(self._server_dir(), exist_ok=True)
        identity.to_file(self._identity_path(identity.hash.hex()))
        hub = RRCHubServer(
            self,
            identity,
            name=name,
            greeting=greeting,
            announce=announce,
            enabled=enabled,
        )
        trusted = self._owner_trusted_hex_list()
        hub.configure_storage(
            self._hub_dir(hub.hub_id),
            trusted=trusted,
            banned=[],
        )
        with self._lock:
            self.hubs.append(hub)
        if enabled:
            with contextlib.suppress(Exception):
                hub.start()
        self.save()
        self._notify_change(hub)
        return hub

    def delete_hub(self, hub_id):
        hub = self.find_hub(hub_id)
        if hub is None:
            return False
        with contextlib.suppress(Exception):
            hub.stop()
        with self._lock:
            if hub in self.hubs:
                self.hubs.remove(hub)
        with contextlib.suppress(Exception):
            path = self._identity_path(hub_id)
            if os.path.isfile(path):
                os.unlink(path)
        with contextlib.suppress(Exception):
            import shutil

            hub_dir = self._hub_dir(hub_id)
            if os.path.isdir(hub_dir):
                shutil.rmtree(hub_dir)
        self.save()
        self._notify_change()
        return True

    def start_hub(self, hub_id):
        hub = self.find_hub(hub_id)
        if hub is None:
            return False
        hub.enabled = True
        with contextlib.suppress(Exception):
            hub.start()
        self.save()
        self._notify_change(hub)
        return True

    def stop_hub(self, hub_id):
        hub = self.find_hub(hub_id)
        if hub is None:
            return False
        hub.enabled = False
        with contextlib.suppress(Exception):
            hub.stop()
        self.save()
        self._notify_change(hub)
        return True

    def update_hub(
        self,
        hub_id,
        name=None,
        greeting=None,
        announce=None,
        trusted_identities=None,
        banned_identities=None,
    ):
        hub = self.find_hub(hub_id)
        if hub is None:
            return False
        if name is not None:
            hub.name = name
        if greeting is not None:
            hub.greeting = greeting or None
        if announce is not None:
            hub.announce = bool(announce)
        if trusted_identities is not None or banned_identities is not None:
            hub.policy.apply_config(
                trusted_list=trusted_identities,
                banned_list=banned_identities,
            )
            hub.policy.save()
        self.save()
        self._notify_change(hub)
        return True

    def create_room(
        self,
        hub_id,
        name,
        topic=None,
        private=False,
        moderated=False,
        invite_only=False,
        topic_ops_only=False,
        no_outside_msgs=False,
        key=None,
    ):
        hub = self.find_hub(hub_id)
        if hub is None:
            return False
        hub.register_room(
            name,
            topic=topic,
            private=private,
            moderated=moderated,
            invite_only=invite_only,
            topic_ops_only=topic_ops_only,
            no_outside_msgs=no_outside_msgs,
            key=key,
        )
        self.save()
        self._notify_change(hub)
        return True

    def delete_room(self, hub_id, name):
        hub = self.find_hub(hub_id)
        if hub is None:
            return False
        hub.unregister_room(name)
        self.save()
        self._notify_change(hub)
        return True

    def load(self):
        if self._loaded:
            return
        self._loaded = True
        path = self._store_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path, "rb") as f:
                obj = proto.decode(f.read())
        except Exception as e:
            RNS.log("Failed to load RRC hub servers: " + str(e), RNS.LOG_ERROR)
            return
        if not isinstance(obj, dict):
            return
        for entry in obj.get("hubs", []):
            self._load_entry(entry)

    def _load_entry(self, entry):
        if not isinstance(entry, dict):
            return
        hub_id = entry.get("id")
        if not isinstance(hub_id, str):
            return
        ident_path = self._identity_path(hub_id)
        if not os.path.isfile(ident_path):
            return
        identity = RNS.Identity.from_file(ident_path)
        if identity is None:
            return
        hub = RRCHubServer(
            self,
            identity,
            name=entry.get("name"),
            greeting=entry.get("greeting"),
            announce=bool(entry.get("announce", True)),
            enabled=bool(entry.get("enabled", True)),
        )
        hub.configure_storage(
            self._hub_dir(hub_id),
            trusted=entry.get("trusted_identities"),
            banned=entry.get("banned_identities"),
        )
        for room in entry.get("rooms", []):
            if isinstance(room, dict) and isinstance(room.get("name"), str):
                rname = proto.normalize_room(room["name"])
                if rname in hub.rooms._registry:
                    continue
                with contextlib.suppress(Exception):
                    hub.register_room(
                        room["name"],
                        topic=room.get("topic"),
                        private=bool(room.get("private")),
                        moderated=bool(room.get("moderated", False)),
                        invite_only=bool(room.get("invite_only", False)),
                        topic_ops_only=bool(room.get("topic_ops_only", False)),
                        no_outside_msgs=bool(room.get("no_outside_msgs", False)),
                        key=room.get("key"),
                    )
        with self._lock:
            self.hubs.append(hub)
        if hub.enabled:
            with contextlib.suppress(Exception):
                hub.start()

    def save(self):
        path = self._store_path()
        tmp_path = path + ".tmp"
        with self._save_lock:
            try:
                with self._lock:
                    entries = [hub.config_entry() for hub in self.hubs]
                os.makedirs(self._server_dir(), exist_ok=True)
                with open(tmp_path, "wb") as f:
                    f.write(proto.encode({"hubs": entries}))
                    f.flush()
                    with contextlib.suppress(Exception):
                        os.fsync(f.fileno())
                os.replace(tmp_path, path)
            except Exception:
                with contextlib.suppress(Exception):
                    os.unlink(tmp_path)

    def to_dict(self):
        """Return a JSON-serializable summary of all hosted hubs."""
        with self._lock:
            hubs = list(self.hubs)
        return {"hubs": [hub.to_dict() for hub in hubs]}

    def shutdown(self):
        for hub in list(self.hubs):
            with contextlib.suppress(Exception):
                hub.stop()
