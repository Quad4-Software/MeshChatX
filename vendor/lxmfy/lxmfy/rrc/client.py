"""RRC client session for connecting bots to hubs over RNS Links."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import RNS

from .constants import (
    B_HELLO_CAPS,
    B_HELLO_NAME,
    B_HELLO_VER,
    B_RES_ENCODING,
    B_RES_ID,
    B_RES_KIND,
    B_RES_SHA256,
    B_RES_SIZE,
    B_WELCOME_CAPS,
    B_WELCOME_HUB,
    B_WELCOME_LIMITS,
    B_WELCOME_VER,
    CAP_ACTION,
    CAP_RESOURCE_ENVELOPE,
    CLIENT_NAME,
    CLIENT_VERSION,
    DEFAULT_DEST_NAME,
    DEFAULT_MAX_MSG_BYTES,
    DEFAULT_MAX_NICK_BYTES,
    DEFAULT_MAX_ROOM_BYTES,
    DEFAULT_MAX_ROOMS,
    DEFAULT_RATE_PER_MINUTE,
    K_BODY,
    K_ID,
    L_MAX_MSG_BODY_BYTES,
    L_MAX_NICK_BYTES,
    L_MAX_ROOM_NAME_BYTES,
    L_MAX_ROOMS_PER_SESSION,
    L_RATE_LIMIT_MSGS_PER_MINUTE,
    MAX_MEMBERS_PER_ROOM,
    MAX_PENDING_PINGS,
    MAX_RESOURCE_EXPECTATIONS,
    MAX_TRACKED_NICKS,
    RES_KIND_MOTD,
    RES_KIND_NOTICE,
    STATUS_CONNECTED,
    STATUS_CONNECTING,
    STATUS_DISCONNECTED,
    STATUS_FAILED,
    STATUS_NAMES,
    T_ACTION,
    T_ERROR,
    T_HELLO,
    T_JOIN,
    T_JOINED,
    T_MSG,
    T_NOTICE,
    T_PART,
    T_PARTED,
    T_PING,
    T_PONG,
    T_RESOURCE_ENVELOPE,
    T_WELCOME,
)
from .envelope import (
    decode_envelope,
    encode_envelope,
    envelope_body,
    envelope_nick,
    envelope_room,
    envelope_src,
    envelope_type,
    make_envelope,
    normalize_room,
    now_ms,
    validate_envelope,
)

logger = logging.getLogger(__name__)

_MENTION_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _mention_re(nick: str) -> re.Pattern[str] | None:
    if not isinstance(nick, str) or not nick:
        return None
    pat = _MENTION_RE_CACHE.get(nick)
    if pat is None:
        pat = re.compile(
            r"(?<![A-Za-z0-9_])@" + re.escape(nick) + r"(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        if len(_MENTION_RE_CACHE) > 32:
            _MENTION_RE_CACHE.clear()
        _MENTION_RE_CACHE[nick] = pat
    return pat


@dataclass
class RRCMessage:
    """A decoded room or session event from an RRC hub."""

    kind: str
    room: str | None
    src: bytes | None
    nick: str | None
    text: str
    ts: int
    hub_hash: bytes | None = None
    mention: bool = False
    raw: dict[int, Any] = field(default_factory=dict, repr=False)


class RRCClient:
    """Client session for a single RRC hub destination."""

    HELLO_ATTEMPTS = 5
    HELLO_INTERVAL_S = 3.0
    CONNECT_TIMEOUT_S = 45.0
    PATH_RETRY_INTERVAL_S = 5.0
    RESOURCE_EXPECTATION_TTL_S = 30.0
    MAX_RESOURCE_BYTES = 262144

    def __init__(
        self,
        identity: RNS.Identity,
        hub_hash: bytes,
        dest_name: str = DEFAULT_DEST_NAME,
        nick: str | None = None,
        auto_reconnect: bool = True,
        client_name: str = CLIENT_NAME,
        client_version: str = CLIENT_VERSION,
        on_event: Callable[[str, RRCClient, Any], None] | None = None,
    ):
        if not isinstance(hub_hash, (bytes, bytearray)) or len(hub_hash) != 16:
            raise ValueError("hub_hash must be a 16-byte destination hash")

        self.identity = identity
        self.hub_hash = bytes(hub_hash)
        self.dest_name = dest_name or DEFAULT_DEST_NAME
        self.nick = nick
        self.auto_reconnect = bool(auto_reconnect)
        self.client_name = client_name
        self.client_version = client_version
        self.on_event = on_event

        self.link: RNS.Link | None = None
        self.status = STATUS_DISCONNECTED
        self.status_text = "Disconnected"
        self.welcomed = False
        self.hub_name: str | None = None
        self.hub_version: str | None = None
        self.hub_caps: dict = {}
        self.motd: str | None = None

        self.max_nick_bytes = DEFAULT_MAX_NICK_BYTES
        self.max_room_name_bytes = DEFAULT_MAX_ROOM_BYTES
        self.max_msg_body_bytes = DEFAULT_MAX_MSG_BYTES
        self.max_rooms_per_session = DEFAULT_MAX_ROOMS
        self.rate_limit_msgs_per_minute = DEFAULT_RATE_PER_MINUTE

        self.rooms: set[str] = set()
        self.members: dict[str, set[bytes]] = {}
        self.nicks: dict[bytes, str] = {}

        self._lock = threading.RLock()
        self._sent_ids: deque[bytes] = deque(maxlen=256)
        self._pending_joins: set[str] = set()
        self._pending_parts: set[str] = set()
        self._pending_pings: dict[bytes, int] = {}
        self._auto_join_rooms: list[str] = []
        self._rejoin_rooms: set[str] = set()
        self._send_timestamps: deque[float] = deque(maxlen=512)
        self._resource_expectations: dict[bytes, dict[str, Any]] = {}

        self._stop_hello = threading.Event()
        self._hello_thread: threading.Thread | None = None
        self._manual_disconnect = False
        self._reconnect_attempts = 0
        self._reconnect_timer: threading.Timer | None = None
        self._announce_handler = None
        self._register_announce_handler()

    @property
    def connected(self) -> bool:
        """True when the session is welcomed and the link is active."""
        return self.status == STATUS_CONNECTED and self.welcomed

    def _src_hash(self) -> bytes:
        """Return this client's identity hash as bytes."""
        src = self.identity.hash
        if not isinstance(src, (bytes, bytearray)) or len(src) != 16:
            raise RuntimeError("identity hash unavailable")
        return bytes(src)

    def set_nick(self, nick: str | None) -> None:
        """Set the advisory nickname used on outgoing envelopes."""
        if nick is not None and nick != "":
            if not isinstance(nick, str):
                raise ValueError("nick must be a string")
            if len(nick.encode("utf-8")) > self.max_nick_bytes:
                raise ValueError("nick too long for hub limit")
        with self._lock:
            self.nick = nick if isinstance(nick, str) and nick else None

    def set_auto_join(self, rooms: list[str] | None) -> None:
        """Configure rooms to join automatically after WELCOME."""
        with self._lock:
            self._auto_join_rooms = [
                normalize_room(r) for r in (rooms or []) if isinstance(r, str)
            ]

    def _track_nick(self, src: bytes, nick: str) -> None:
        self.nicks[src] = nick
        while len(self.nicks) > MAX_TRACKED_NICKS:
            self.nicks.pop(next(iter(self.nicks)))

    def _track_member(self, room: str, src: bytes) -> None:
        members = self.members.setdefault(room, set())
        if src in members:
            return
        if len(members) >= MAX_MEMBERS_PER_ROOM:
            return
        members.add(src)

    def _remember_resource_expectation(self, rid: bytes, meta: dict[str, Any]) -> None:
        while len(self._resource_expectations) >= MAX_RESOURCE_EXPECTATIONS:
            oldest = next(iter(self._resource_expectations))
            self._resource_expectations.pop(oldest, None)
        self._resource_expectations[rid] = meta

    def _emit(self, event: str, payload: Any = None) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(event, self, payload)
        except Exception:
            logger.exception("RRC event handler failed for %s", event)

    def _set_status(self, status: int, text: str | None = None) -> None:
        self.status = status
        if text is not None:
            self.status_text = text
        label = {
            STATUS_DISCONNECTED: "disconnected",
            STATUS_CONNECTING: "connecting",
            STATUS_CONNECTED: "connected",
            STATUS_FAILED: "failed",
        }.get(status, str(status))
        hub = self.hub_hash.hex()
        detail = text or label
        RNS.log(f"RRC [{hub[:12]}…] {detail}", RNS.LOG_INFO)
        self._emit("status", {"status": status, "text": self.status_text})

    def connect(self) -> None:
        """Begin connecting to the hub in a background thread."""
        with self._lock:
            if self.status in (STATUS_CONNECTING, STATUS_CONNECTED):
                return
            self._manual_disconnect = False
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
            text = (
                f"Reconnecting (attempt {self._reconnect_attempts})"
                if self._reconnect_attempts > 0
                else "Connecting"
            )
            self._set_status(STATUS_CONNECTING, text)

        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _register_announce_handler(self) -> None:
        """Listen for the hub announce so reconnect can proceed once keys arrive."""
        if self._announce_handler is not None:
            return
        client = self

        class _HubAnnounceHandler:
            aspect_filter = None
            receive_path_responses = True

            def received_announce(
                self,
                destination_hash,
                announced_identity,
                app_data,
                *args,
                **kwargs,
            ):
                if destination_hash != client.hub_hash:
                    return
                RNS.log(
                    f"RRC [{client.hub_hash.hex()[:12]}…] hub announce received",
                    RNS.LOG_INFO,
                )
                if client.status in (STATUS_FAILED, STATUS_DISCONNECTED):
                    if client.auto_reconnect and not client._manual_disconnect:
                        client.connect()

        self._announce_handler = _HubAnnounceHandler()
        try:
            RNS.Transport.register_announce_handler(self._announce_handler)
        except Exception:
            logger.debug("RRC announce handler registration failed", exc_info=True)
            self._announce_handler = None

    def _deregister_announce_handler(self) -> None:
        handler = self._announce_handler
        self._announce_handler = None
        if handler is None:
            return
        try:
            RNS.Transport.deregister_announce_handler(handler)
        except Exception:
            logger.debug("RRC announce handler deregistration failed", exc_info=True)

    def _connect_worker(self) -> None:
        try:
            timeout_s = self.CONNECT_TIMEOUT_S
            self._set_status(
                STATUS_CONNECTING,
                "Waiting for hub path/announce",
            )

            # Prefer the blocking path helper when available.
            path_ok = False
            try:
                path_ok = bool(
                    RNS.Transport.await_path(self.hub_hash, timeout=timeout_s),
                )
            except Exception:
                path_ok = False

            if not path_ok:
                # Fallback: keep requesting while we wait for Identity.recall.
                deadline = time.monotonic() + timeout_s
                next_request = 0.0
                while time.monotonic() < deadline:
                    now = time.monotonic()
                    if now >= next_request:
                        RNS.Transport.request_path(self.hub_hash)
                        next_request = now + self.PATH_RETRY_INTERVAL_S
                    if RNS.Transport.has_path(self.hub_hash):
                        path_ok = True
                        break
                    if RNS.Identity.recall(self.hub_hash) is not None:
                        path_ok = True
                        break
                    time.sleep(0.2)

            hub_identity = RNS.Identity.recall(self.hub_hash)
            if hub_identity is None:
                # Path may exist before keys are fully recalled; wait a bit more.
                deadline = time.monotonic() + min(10.0, timeout_s)
                while time.monotonic() < deadline:
                    hub_identity = RNS.Identity.recall(self.hub_hash)
                    if hub_identity is not None:
                        break
                    time.sleep(0.2)

            if hub_identity is None:
                self._set_status(
                    STATUS_FAILED,
                    "Hub identity unknown (waiting for hub announce on this Reticulum network)",
                )
                self._maybe_reconnect()
                return

            app_name, aspects = RNS.Destination.app_and_aspects_from_name(
                self.dest_name,
            )
            hub_dest = RNS.Destination(
                hub_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                app_name,
                *aspects,
            )
            if hub_dest.hash != self.hub_hash:
                self._set_status(
                    STATUS_FAILED,
                    f"Hash/destination name mismatch (expected {self.dest_name})",
                )
                self._maybe_reconnect()
                return

            self._set_status(STATUS_CONNECTING, "Opening link to hub")
            self._stop_hello.clear()
            link = RNS.Link(
                hub_dest,
                established_callback=self._on_established,
                closed_callback=self._on_closed,
            )
            link.set_packet_callback(lambda data, _pkt: self._on_packet(data))
            with self._lock:
                self.link = link
        except Exception as exc:
            self._set_status(STATUS_FAILED, f"Connect error: {exc}")
            self._maybe_reconnect()

    def _on_established(self, link: RNS.Link) -> None:
        try:
            link.identify(self.identity)
        except Exception as exc:
            logger.error("RRC identify failed: %s", exc)
            try:
                link.teardown()
            except Exception:
                pass
            return

        try:
            link.set_resource_strategy(RNS.Link.ACCEPT_APP)
            link.set_resource_callback(self._resource_advertised)
            link.set_resource_started_callback(self._resource_advertised)
            link.set_resource_concluded_callback(self._resource_concluded)
        except Exception:
            logger.debug(
                "RRC resource callbacks unavailable on this link",
                exc_info=True,
            )

        self._set_status(STATUS_CONNECTING, "Identified, sending HELLO")

        def hello_loop() -> None:
            attempts = 0
            while (
                not self._stop_hello.is_set()
                and not self.welcomed
                and attempts < self.HELLO_ATTEMPTS
            ):
                with self._lock:
                    cur_link = self.link
                if cur_link is None or cur_link.status != RNS.Link.ACTIVE:
                    return
                try:
                    self._send_hello(cur_link)
                except Exception as exc:
                    logger.error("RRC HELLO send failed: %s", exc)
                attempts += 1
                self._stop_hello.wait(timeout=self.HELLO_INTERVAL_S)

            if not self.welcomed and not self._stop_hello.is_set():
                self._set_status(STATUS_FAILED, "WELCOME timeout")
                try:
                    with self._lock:
                        if self.link is not None:
                            self.link.teardown()
                except Exception:
                    pass

        self._hello_thread = threading.Thread(target=hello_loop, daemon=True)
        self._hello_thread.start()

    def _send_hello(self, link: RNS.Link) -> None:
        body = {
            B_HELLO_NAME: self.client_name,
            B_HELLO_VER: self.client_version,
            B_HELLO_CAPS: {
                CAP_RESOURCE_ENVELOPE: True,
                CAP_ACTION: True,
            },
        }
        env = make_envelope(T_HELLO, src=self._src_hash(), body=body, nick=self.nick)
        payload = encode_envelope(env)
        RNS.Packet(link, payload).send()

    def _reset_session_state(self, *, preserve_rejoin: bool) -> None:
        with self._lock:
            if preserve_rejoin:
                self._rejoin_rooms |= set(self.rooms)
            else:
                self._rejoin_rooms.clear()
            self.link = None
            self.welcomed = False
            self.motd = None
            self.rooms.clear()
            self.members.clear()
            self.nicks.clear()
            self._pending_joins.clear()
            self._pending_parts.clear()
            self._pending_pings.clear()
            self._resource_expectations.clear()
            self._send_timestamps.clear()

    def _on_closed(self, _link: RNS.Link) -> None:
        self._stop_hello.set()
        with self._lock:
            should_reconnect = self.auto_reconnect and not self._manual_disconnect
            preserve_rejoin = not self._manual_disconnect
        self._reset_session_state(preserve_rejoin=preserve_rejoin)
        self._set_status(STATUS_DISCONNECTED, "Disconnected")
        if should_reconnect:
            self._schedule_reconnect()

    def _maybe_reconnect(self) -> None:
        if self.auto_reconnect and not self._manual_disconnect:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        with self._lock:
            self._reconnect_attempts += 1
            backoff = min(60.0, max(1.0, 2.0 ** min(self._reconnect_attempts, 6)))
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()

            def fire() -> None:
                with self._lock:
                    self._reconnect_timer = None
                    if self._manual_disconnect or not self.auto_reconnect:
                        return
                self.connect()

            self._reconnect_timer = threading.Timer(backoff, fire)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()
            self._set_status(
                STATUS_DISCONNECTED,
                f"Reconnect in {int(backoff)}s",
            )

    def disconnect(self) -> None:
        """Tear down the session and cancel reconnect."""
        self._stop_hello.set()
        with self._lock:
            self._manual_disconnect = True
            self._reconnect_attempts = 0
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
            link = self.link
            self.link = None
        if link is not None:
            try:
                link.teardown()
            except Exception:
                pass
        self._reset_session_state(preserve_rejoin=False)
        self._deregister_announce_handler()
        self._set_status(STATUS_DISCONNECTED, "Disconnected")

    def _packet_would_fit(self, link: RNS.Link, payload: bytes) -> bool:
        try:
            pkt = RNS.Packet(link, payload)
            pkt.pack()
            return True
        except Exception:
            return False

    def _check_rate_limit(self) -> None:
        limit = self.rate_limit_msgs_per_minute
        if not isinstance(limit, int) or limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            while self._send_timestamps and now - self._send_timestamps[0] > 60.0:
                self._send_timestamps.popleft()
            if len(self._send_timestamps) >= limit:
                raise RuntimeError("client rate limit exceeded")
            self._send_timestamps.append(now)

    def _send_env(
        self,
        env: dict[int, Any],
        *,
        allow_pre_welcome: bool = False,
    ) -> None:
        msg_type = envelope_type(env)
        with self._lock:
            link = self.link
            if link is None or link.status != RNS.Link.ACTIVE:
                raise RuntimeError("not connected")
            if not allow_pre_welcome and not self.welcomed and msg_type != T_PONG:
                raise RuntimeError("session not welcomed yet")
            payload = encode_envelope(env)
            if not self._packet_would_fit(link, payload):
                raise RuntimeError("message exceeds link MTU")
            RNS.Packet(link, payload).send()

    def join(self, room: str, key: str | None = None) -> str:
        """Request membership in a room. Returns the normalized room name."""
        room_n = normalize_room(room)
        if len(room_n.encode("utf-8")) > self.max_room_name_bytes:
            raise ValueError("room name too long for hub limit")
        with self._lock:
            projected = len(self.rooms | self._pending_joins | {room_n})
            if projected > self.max_rooms_per_session:
                raise RuntimeError("max rooms per session exceeded")
            self._pending_joins.add(room_n)
            self._rejoin_rooms.add(room_n)
        body = key if isinstance(key, str) and key else None
        env = make_envelope(
            T_JOIN,
            src=self._src_hash(),
            room=room_n,
            body=body,
            nick=self.nick,
        )
        self._send_env(env)
        return room_n

    def part(self, room: str) -> str:
        """Leave a room. Returns the normalized room name."""
        room_n = normalize_room(room)
        env = make_envelope(
            T_PART,
            src=self._src_hash(),
            room=room_n,
            nick=self.nick,
        )
        with self._lock:
            self._pending_parts.add(room_n)
            self._rejoin_rooms.discard(room_n)
        try:
            self._send_env(env)
        except Exception as exc:
            logger.warning("RRC PART send failed for #%s: %s", room_n, exc)
            with self._lock:
                self._pending_parts.discard(room_n)
                self._rejoin_rooms.add(room_n)
            raise
        with self._lock:
            self.rooms.discard(room_n)
            self.members.pop(room_n, None)
        return room_n

    def send_message(self, room: str, text: str) -> bytes:
        """Send a MSG to a room. Returns the message id."""
        return self._send_room_text(T_MSG, room, text, "msg")

    def send_notice(self, room: str, text: str) -> bytes:
        """Send a NOTICE to a room. Returns the message id."""
        return self._send_room_text(T_NOTICE, room, text, "notice")

    def send_action(self, room: str, text: str) -> bytes:
        """Send an ACTION to a room. Returns the message id."""
        return self._send_room_text(T_ACTION, room, text, "action")

    def _send_room_text(
        self,
        msg_type: int,
        room: str,
        text: str,
        kind: str,
    ) -> bytes:
        room_n = normalize_room(room)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{kind} text must be non-empty")
        if len(text.encode("utf-8")) > self.max_msg_body_bytes:
            raise ValueError(f"{kind} too long for hub limit")
        self._check_rate_limit()
        env = make_envelope(
            msg_type,
            src=self._src_hash(),
            room=room_n,
            body=text,
            nick=self.nick,
        )
        mid = env[K_ID]
        if isinstance(mid, (bytes, bytearray)):
            self._sent_ids.append(bytes(mid))
        self._send_env(env)
        return bytes(mid)

    def send_command(self, text: str, room: str | None = None) -> None:
        """Send a slash command as a MSG body."""
        if not isinstance(text, str) or not text.startswith("/"):
            raise ValueError("command must start with /")
        room_n = normalize_room(room) if room else None
        self._check_rate_limit()
        env = make_envelope(
            T_MSG,
            src=self._src_hash(),
            room=room_n,
            body=text,
            nick=self.nick,
        )
        self._send_env(env)

    def ping(self) -> bytes:
        """Send a PING and return the correlation body."""
        body = os.urandom(8)
        env = make_envelope(T_PING, src=self._src_hash(), body=body)
        with self._lock:
            now = now_ms()
            self._pending_pings[body] = now
            expired = [k for k, v in self._pending_pings.items() if now - v > 15000]
            for key in expired:
                self._pending_pings.pop(key, None)
            while len(self._pending_pings) > MAX_PENDING_PINGS:
                oldest = next(iter(self._pending_pings))
                self._pending_pings.pop(oldest, None)
        self._send_env(env)
        return body

    def _on_packet(self, data: bytes | bytearray) -> None:
        env = decode_envelope(data)
        if env is None:
            logger.debug("RRC decode failed for %d bytes", len(data))
            self._emit("decode_error", {"size": len(data)})
            return
        if not validate_envelope(env):
            logger.debug("RRC envelope failed validation")
            self._emit("decode_error", {"reason": "invalid_envelope"})
            return
        msg_type = envelope_type(env)
        if msg_type is None:
            return

        if msg_type == T_PING:
            try:
                pong = make_envelope(
                    T_PONG,
                    src=self._src_hash(),
                    body=env.get(K_BODY),
                )
                self._send_env(pong, allow_pre_welcome=True)
            except Exception:
                pass
            return

        if msg_type == T_PONG:
            body = env.get(K_BODY)
            if isinstance(body, (bytes, bytearray)):
                key = bytes(body)
                with self._lock:
                    sent = self._pending_pings.pop(key, None)
                if sent is not None:
                    rtt = max(0, now_ms() - sent)
                    self._emit("pong", {"rtt_ms": rtt, "body": key})
            return

        if msg_type == T_WELCOME:
            self._handle_welcome(env)
            return

        if msg_type == T_JOINED:
            self._handle_joined(env)
            return

        if msg_type == T_PARTED:
            self._handle_parted(env)
            return

        if msg_type in (T_MSG, T_NOTICE, T_ACTION):
            self._handle_room_content(env, msg_type)
            return

        if msg_type == T_ERROR:
            text = envelope_body(env)
            if not isinstance(text, str):
                text = "(error)"
            room = envelope_room(env)
            with self._lock:
                if room and room in self._pending_joins:
                    self._pending_joins.discard(room)
                    self.rooms.discard(room)
                    self._rejoin_rooms.discard(room)
                if room:
                    self._pending_parts.discard(room)
            msg = RRCMessage(
                kind="error",
                room=room,
                src=None,
                nick=None,
                text=text,
                ts=now_ms(),
                hub_hash=self.hub_hash,
                raw=env,
            )
            self._emit("error", msg)
            return

        if msg_type == T_RESOURCE_ENVELOPE:
            self._handle_resource_envelope(env)
            return

    def _handle_resource_envelope(self, env: dict[int, Any]) -> None:
        body = envelope_body(env)
        if not isinstance(body, dict):
            return
        try:
            rid = body.get(B_RES_ID)
            kind = body.get(B_RES_KIND)
            size = body.get(B_RES_SIZE)
            sha256 = body.get(B_RES_SHA256)
            encoding = body.get(B_RES_ENCODING)
            if not isinstance(rid, (bytes, bytearray)):
                return
            if not isinstance(kind, str):
                return
            if not isinstance(size, int) or size <= 0:
                return
            room = envelope_room(env)
            with self._lock:
                self._remember_resource_expectation(
                    bytes(rid),
                    {
                        "kind": kind,
                        "size": size,
                        "sha256": bytes(sha256)
                        if isinstance(sha256, (bytes, bytearray))
                        else None,
                        "encoding": encoding if isinstance(encoding, str) else "utf-8",
                        "room": room,
                        "expires": time.monotonic() + self.RESOURCE_EXPECTATION_TTL_S,
                    },
                )
        except Exception:
            logger.debug("RRC resource envelope parse failed", exc_info=True)

    def _resource_advertised(self, resource) -> bool:
        try:
            if hasattr(resource, "get_data_size"):
                size = resource.get_data_size()
            elif hasattr(resource, "total_size"):
                size = resource.total_size
            else:
                size = getattr(resource, "size", 0)
        except Exception:
            return False
        if not isinstance(size, int) or size <= 0 or size > self.MAX_RESOURCE_BYTES:
            return False
        return True

    def _resource_concluded(self, resource) -> None:
        try:
            if resource.status != RNS.Resource.COMPLETE:
                try:
                    if hasattr(resource, "data") and resource.data:
                        resource.data.close()
                except Exception:
                    pass
                return
            data = None
            try:
                data = resource.data.read()
            finally:
                try:
                    if hasattr(resource, "data") and resource.data:
                        resource.data.close()
                except Exception:
                    pass
            if data is None:
                return

            now = time.monotonic()
            matched = None
            with self._lock:
                expired = [
                    k
                    for k, v in self._resource_expectations.items()
                    if v["expires"] < now
                ]
                for key in expired:
                    self._resource_expectations.pop(key, None)
                for key, exp in list(self._resource_expectations.items()):
                    if exp["size"] == len(data):
                        matched = exp
                        self._resource_expectations.pop(key, None)
                        break

            kind = matched["kind"] if matched else "blob"
            room = matched["room"] if matched else None
            encoding = matched["encoding"] if matched else "utf-8"
            sha = matched["sha256"] if matched else None
            if sha is not None and hashlib.sha256(data).digest() != sha:
                logger.warning("RRC resource SHA256 mismatch")
                return
            if kind in (RES_KIND_NOTICE, RES_KIND_MOTD):
                text = data.decode(encoding, errors="replace")
                if kind == RES_KIND_MOTD:
                    with self._lock:
                        self.motd = text
                    self._emit("motd", text)
                msg = RRCMessage(
                    kind="notice",
                    room=room,
                    src=None,
                    nick=None,
                    text=text,
                    ts=now_ms(),
                    hub_hash=self.hub_hash,
                )
                self._emit("notice", msg)
        except Exception:
            logger.exception("RRC resource handling failed")

    def _handle_welcome(self, env: dict[int, Any]) -> None:
        self.welcomed = True
        body = envelope_body(env)
        if isinstance(body, dict):
            hub_name = body.get(B_WELCOME_HUB)
            if isinstance(hub_name, str):
                self.hub_name = hub_name
            ver = body.get(B_WELCOME_VER)
            if isinstance(ver, str):
                self.hub_version = ver
            caps = body.get(B_WELCOME_CAPS)
            if isinstance(caps, dict):
                self.hub_caps = dict(caps)
            limits = body.get(B_WELCOME_LIMITS)
            if isinstance(limits, dict):
                if L_MAX_NICK_BYTES in limits:
                    self.max_nick_bytes = int(limits[L_MAX_NICK_BYTES])
                if L_MAX_ROOM_NAME_BYTES in limits:
                    self.max_room_name_bytes = int(limits[L_MAX_ROOM_NAME_BYTES])
                if L_MAX_MSG_BODY_BYTES in limits:
                    self.max_msg_body_bytes = int(limits[L_MAX_MSG_BODY_BYTES])
                if L_MAX_ROOMS_PER_SESSION in limits:
                    self.max_rooms_per_session = int(limits[L_MAX_ROOMS_PER_SESSION])
                if L_RATE_LIMIT_MSGS_PER_MINUTE in limits:
                    self.rate_limit_msgs_per_minute = int(
                        limits[L_RATE_LIMIT_MSGS_PER_MINUTE],
                    )
        with self._lock:
            self._reconnect_attempts = 0
            rooms_to_join = sorted(set(self._auto_join_rooms) | set(self._rejoin_rooms))
        self._set_status(STATUS_CONNECTED, "Connected")
        self._emit(
            "welcome", {"hub_name": self.hub_name, "hub_version": self.hub_version}
        )
        if rooms_to_join:
            RNS.log(
                f"RRC auto-joining rooms: {', '.join('#' + r for r in rooms_to_join)}",
                RNS.LOG_INFO,
            )
        else:
            RNS.log("RRC welcomed but no rooms configured to join", RNS.LOG_WARNING)
        for room in rooms_to_join:
            try:
                self.join(room)
            except Exception:
                logger.exception("Auto-join failed for room %s", room)
                RNS.log(f"RRC auto-join failed for #{room}", RNS.LOG_ERROR)

    def _handle_joined(self, env: dict[int, Any]) -> None:
        room = envelope_room(env)
        if not room:
            return
        body = envelope_body(env)
        joiner_nick = envelope_nick(env)
        own_hash = self._src_hash()
        body_hashes = []
        if isinstance(body, list):
            body_hashes = [
                bytes(entry) for entry in body if isinstance(entry, (bytes, bytearray))
            ]

        with self._lock:
            self_join = room in self._pending_joins
            if self_join:
                self._pending_joins.discard(room)
            self.rooms.add(room)
            self._rejoin_rooms.add(room)
            for hash_bytes in body_hashes:
                self._track_member(room, hash_bytes)
            self._track_member(room, own_hash)
            if (
                not self_join
                and isinstance(joiner_nick, str)
                and joiner_nick
                and len(body_hashes) == 1
            ):
                joiner = body_hashes[0]
                if joiner != own_hash:
                    self._track_nick(joiner, joiner_nick)

        if self_join:
            RNS.log(f"RRC joined #{room}", RNS.LOG_INFO)

        msg = RRCMessage(
            kind="joined",
            room=room,
            src=body_hashes[0] if len(body_hashes) == 1 else None,
            nick=joiner_nick,
            text=room,
            ts=now_ms(),
            hub_hash=self.hub_hash,
            raw=env,
        )
        self._emit("joined", msg)

    def _handle_parted(self, env: dict[int, Any]) -> None:
        room = envelope_room(env)
        if not room:
            return
        body = envelope_body(env)
        parter_nick = envelope_nick(env)
        own_hash = self._src_hash()
        body_hashes = []
        if isinstance(body, list):
            body_hashes = [
                bytes(entry) for entry in body if isinstance(entry, (bytes, bytearray))
            ]

        with self._lock:
            self_part = room in self._pending_parts
            if self_part:
                self._pending_parts.discard(room)
            if (
                not self_part
                and isinstance(parter_nick, str)
                and parter_nick
                and len(body_hashes) == 1
            ):
                parter = body_hashes[0]
                if parter != own_hash:
                    self.nicks[parter] = parter_nick
            members = self.members.get(room)
            if members is not None:
                for hash_bytes in body_hashes:
                    members.discard(hash_bytes)
            if self_part:
                self.rooms.discard(room)
                self.members.pop(room, None)
                self._rejoin_rooms.discard(room)

        msg = RRCMessage(
            kind="parted",
            room=room,
            src=body_hashes[0] if len(body_hashes) == 1 else None,
            nick=parter_nick,
            text=room,
            ts=now_ms(),
            hub_hash=self.hub_hash,
            raw=env,
        )
        self._emit("parted", msg)

    def _handle_room_content(self, env: dict[int, Any], msg_type: int) -> None:
        body = envelope_body(env)
        room = envelope_room(env)
        src = envelope_src(env)
        nick = envelope_nick(env)
        mid = env.get(K_ID)
        own_hash = self._src_hash()

        if src is not None and src == own_hash:
            if isinstance(mid, (bytes, bytearray)) and bytes(mid) in self._sent_ids:
                return

        if src is not None and nick:
            with self._lock:
                self._track_nick(src, nick)
                if room:
                    self._track_member(room, src)

        kind = {T_MSG: "msg", T_NOTICE: "notice", T_ACTION: "action"}[msg_type]

        if (
            msg_type == T_NOTICE
            and room is None
            and isinstance(body, str)
            and body.strip()
        ):
            with self._lock:
                self.motd = body
            self._emit("motd", body)

        if not isinstance(body, str):
            return

        mention = False
        if src != own_hash and self.nick:
            pat = _mention_re(self.nick)
            if pat is not None and pat.search(body):
                mention = True

        msg = RRCMessage(
            kind=kind,
            room=room,
            src=src,
            nick=nick,
            text=body,
            ts=now_ms(),
            hub_hash=self.hub_hash,
            mention=mention,
            raw=env,
        )
        self._emit(kind, msg)

    def status_dict(self) -> dict[str, Any]:
        """Return a serializable status snapshot."""
        with self._lock:
            return {
                "hub_hash": self.hub_hash.hex(),
                "dest_name": self.dest_name,
                "status": STATUS_NAMES.get(self.status, str(self.status)),
                "status_text": self.status_text,
                "welcomed": self.welcomed,
                "hub_name": self.hub_name,
                "hub_version": self.hub_version,
                "nick": self.nick,
                "rooms": sorted(self.rooms),
                "rejoin_rooms": sorted(self._rejoin_rooms),
                "motd": self.motd,
                "max_msg_body_bytes": self.max_msg_body_bytes,
                "max_rooms_per_session": self.max_rooms_per_session,
                "rate_limit_msgs_per_minute": self.rate_limit_msgs_per_minute,
            }
