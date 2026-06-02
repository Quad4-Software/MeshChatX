# SPDX-License-Identifier: 0BSD

"""Reticulum Relay Chat session management.

Contains :class:`RRCHub`, which owns the Reticulum link and protocol state for a
single hub, and :class:`RRCManager`, which tracks the set of configured hubs,
persists them, and relays change and message notifications to the application.
"""

import contextlib
import hashlib
import os
import re
import threading
import time
from collections import deque

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.server import _LoopbackEndpoint

HISTORY_DIR_NAME = "rrc_history"
HISTORY_FILENAME_SANITIZE_RE = re.compile(r"[^a-z0-9._-]+")

H_KIND = "k"
H_SRC = "s"
H_NICK = "n"
H_TEXT = "t"
H_TS = "ts"
H_MENTION = "m"


class RRCHub:
    """A single RRC hub connection and its associated rooms and history."""

    STATUS_DISCONNECTED = 0
    STATUS_CONNECTING = 1
    STATUS_CONNECTED = 2
    STATUS_FAILED = 3

    CLEAN_HISTORY_INTERVAL = 5
    SYS_NOTICE_TIMEOUT = 600

    def __init__(self, manager, hub_hash, dest_name=None, name=None):
        self.manager = manager
        self.hub_hash = hub_hash
        self.dest_name = dest_name or proto.DEFAULT_DEST_NAME
        self.name = name or RNS.prettyhexrep(hub_hash)

        self.link = None
        self.status = RRCHub.STATUS_DISCONNECTED
        self.status_text = "Disconnected"
        self.welcomed = False
        self.hub_name = None
        self.hub_version = None
        self.hub_caps = {}
        self.motd = None

        self.max_nick_bytes = proto.DEFAULT_MAX_NICK_BYTES
        self.max_room_name_bytes = proto.DEFAULT_MAX_ROOM_BYTES
        self.max_msg_body_bytes = proto.DEFAULT_MAX_MSG_BYTES
        self.max_rooms_per_session = proto.DEFAULT_MAX_ROOMS
        self.rate_limit_msgs_per_minute = proto.DEFAULT_RATE_PER_MINUTE

        self.rooms = set()
        self.messages = {}
        self.notices = []
        self.unread_rooms = set()
        self.unread_counts = {}
        self.mention_rooms = set()
        self.members = {}
        self.nicks = {}

        self.auto_reconnect = True
        self.custom_name = None
        self.hub_icon = None
        self.room_order = []
        self.auto_list = False
        self.auto_who = False

        self._lock = threading.RLock()
        self._resource_expectations = {}
        self._sent_ids = deque(maxlen=256)

        self._hello_thread = None
        self._stop_hello = threading.Event()
        self._manual_disconnect = False
        self._reconnect_attempts = 0
        self._reconnect_timer = None
        self._pending_pings = {}
        self._last_history_clean = 0
        self.clean_last_removed = 0

        self.available_rooms = {}
        self._silent_list_pending = 0
        self._silent_who_rooms = set()

        self.nick_override = None
        self._pending_joins = set()
        self._pending_parts = set()
        self._silent_joins = set()

        self._history_write_failed = False

    def _log(self, msg, level=None):
        if level is None:
            level = RNS.LOG_INFO
        RNS.log("[RRC " + self.name + "] " + msg, level)

    def add_room(self, room):
        room_n = proto.normalize_room(room)
        with self._lock:
            self.rooms.add(room_n)
            if room_n not in self.messages:
                self.messages[room_n] = []
        self.manager.save()
        self.manager._notify_change(self)
        return room_n

    def remove_room(self, room):
        r = proto.normalize_room(room)
        with self._lock:
            self.rooms.discard(r)
            self.messages.pop(r, None)
            self.unread_rooms.discard(r)
            self.unread_counts.pop(r, None)
            self.mention_rooms.discard(r)
            self.members.pop(r, None)
        self._delete_history(r)
        self.manager.save()
        self.manager._notify_change(self)

    def clear_messages(self, room):
        r = proto.normalize_room(room)
        with self._lock:
            if r in self.messages:
                self.messages[r] = []
            self.unread_rooms.discard(r)
            self.unread_counts.pop(r, None)
            self.mention_rooms.discard(r)
        self._delete_history(r)
        self.manager._notify_change(self)

    def get_members(self, room):
        with self._lock:
            return list(self.members.get(room, set()))

    def display_name_for(self, peer):
        if not isinstance(peer, (bytes, bytearray)):
            return "<unknown>"
        ph = bytes(peer)
        with self._lock:
            nick = self.nicks.get(ph)
        if nick:
            return nick
        resolver = self.manager.get_name_for_identity_hash
        if resolver is not None:
            with contextlib.suppress(Exception):
                resolved = resolver(ph)
                if isinstance(resolved, str) and resolved:
                    return resolved
        return ph.hex()[:12]

    def mark_read(self, room):
        r = proto.normalize_room(room)
        with self._lock:
            self.unread_rooms.discard(r)
            self.unread_counts.pop(r, None)
            self.mention_rooms.discard(r)
        self.manager._notify_change(self)

    def get_display_name(self):
        with self._lock:
            if isinstance(self.custom_name, str) and self.custom_name.strip():
                return self.custom_name.strip()
            if isinstance(self.hub_name, str) and self.hub_name.strip():
                return self.hub_name.strip()
            return self.name

    def set_custom_name(self, name, save=True):
        with self._lock:
            if name is None or (isinstance(name, str) and not name.strip()):
                self.custom_name = None
            else:
                self.custom_name = str(name).strip()
        if save:
            self.manager.save()
        self.manager._notify_change(self)

    def get_hub_icon(self):
        with self._lock:
            if isinstance(self.hub_icon, str) and self.hub_icon.strip():
                return self.hub_icon.strip()
            return None

    def ordered_known_rooms(self):
        with self._lock:
            known = set(self.messages.keys()) | self.rooms
            ordered = []
            seen = set()
            for room in self.room_order:
                if not isinstance(room, str):
                    continue
                rn = room.strip().lower()
                if rn and rn in known and rn not in seen:
                    ordered.append(rn)
                    seen.add(rn)
            for room in sorted(known - seen):
                ordered.append(room)
            return ordered

    def reorder_rooms(self, room_names):
        if not isinstance(room_names, list):
            return False
        known = set(self.ordered_known_rooms())
        order = []
        for name in room_names:
            if not isinstance(name, str):
                continue
            try:
                rn = proto.normalize_room(name)
            except ValueError:
                continue
            if rn in known and rn not in order:
                order.append(rn)
        with self._lock:
            remaining = [r for r in known if r not in order]
            self.room_order = order + sorted(remaining)
        self.manager.save()
        self.manager._notify_change(self)
        return True

    def set_hub_icon(self, icon_name, save=True):
        from meshchatx.src.backend.mdi_icon_util import normalize_mdi_icon_name

        normalized = normalize_mdi_icon_name(icon_name)
        with self._lock:
            self.hub_icon = normalized
        if save:
            self.manager.save()
        self.manager._notify_change(self)

    def _bump_unread(self, room):
        if not room:
            return
        self.unread_rooms.add(room)
        self.unread_counts[room] = min(9999, self.unread_counts.get(room, 0) + 1)

    def _set_status(self, status, text=None):
        self.status = status
        if text is not None:
            self.status_text = text
        self.manager._notify_change(self)

    def connect(self):
        with self._lock:
            if self.status in (RRCHub.STATUS_CONNECTING, RRCHub.STATUS_CONNECTED):
                return
            self._manual_disconnect = False
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
            if self._reconnect_attempts > 0:
                text = "Reconnecting (attempt " + str(self._reconnect_attempts) + ")"
            else:
                text = "Connecting"
            self._set_status(RRCHub.STATUS_CONNECTING, text)

        t = threading.Thread(target=self._connect_worker, daemon=True)
        t.start()

    def _connect_loopback(self, server):
        self._stop_hello.clear()
        link = _LoopbackEndpoint(self, server)
        server._attach_loopback(link, self.manager.identity)
        with self._lock:
            self.link = link
        self._set_status(RRCHub.STATUS_CONNECTING, "Connected locally, sending HELLO")
        self._hello_thread = threading.Thread(target=self._hello_loop, daemon=True)
        self._hello_thread.start()

    def _connect_worker(self):
        try:
            server = self.manager.find_local_server(self.hub_hash)
            if server is not None:
                self._connect_loopback(server)
                return

            timeout_s = 20.0
            if not RNS.Transport.has_path(self.hub_hash):
                RNS.Transport.request_path(self.hub_hash)
                deadline = time.monotonic() + min(5.0, timeout_s)
                while time.monotonic() < deadline:
                    if RNS.Transport.has_path(self.hub_hash):
                        break
                    time.sleep(0.1)

            hub_identity = None
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                hub_identity = RNS.Identity.recall(self.hub_hash)
                if hub_identity is not None:
                    break
                time.sleep(0.2)

            if hub_identity is None:
                self._set_status(RRCHub.STATUS_FAILED, "Hub identity unknown")
                self._maybe_schedule_reconnect_after_failed_connect()
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
                    RRCHub.STATUS_FAILED,
                    "Hash/destination name mismatch",
                )
                self._maybe_schedule_reconnect_after_failed_connect()
                return

            self._stop_hello.clear()
            link = RNS.Link(
                hub_dest,
                established_callback=self._on_established,
                closed_callback=self._on_closed,
            )
            link.set_packet_callback(lambda data, pkt: self._on_packet(data))
            with self._lock:
                self.link = link
        except Exception as e:
            self._set_status(RRCHub.STATUS_FAILED, "Connect error: " + str(e))
            self._maybe_schedule_reconnect_after_failed_connect()

    def _maybe_schedule_reconnect_after_failed_connect(self):
        with self._lock:
            if self._manual_disconnect or not self.auto_reconnect:
                return
            if self.link is not None:
                return
        self._schedule_reconnect()

    def _on_established(self, link):
        with contextlib.suppress(Exception):
            link.set_resource_strategy(RNS.Link.ACCEPT_APP)
            link.set_resource_callback(self._resource_advertised)
            link.set_resource_started_callback(self._resource_advertised)
            link.set_resource_concluded_callback(self._resource_concluded)

        try:
            link.identify(self.manager.identity)
        except Exception as e:
            self._log("identify failed: " + str(e), RNS.LOG_ERROR)
            with contextlib.suppress(Exception):
                link.teardown()
            return

        self._set_status(RRCHub.STATUS_CONNECTING, "Identified, sending HELLO")

        self._hello_thread = threading.Thread(target=self._hello_loop, daemon=True)
        self._hello_thread.start()

    def _hello_loop(self):
        attempts = 0
        while not self._stop_hello.is_set() and not self.welcomed and attempts < 5:
            with self._lock:
                cur_link = self.link
            if cur_link is None or cur_link.status != RNS.Link.ACTIVE:
                return
            try:
                self._send_hello(cur_link)
            except Exception as e:
                self._log("HELLO send failed: " + str(e), RNS.LOG_ERROR)
            attempts += 1
            self._stop_hello.wait(timeout=3.0)
        if not self.welcomed and not self._stop_hello.is_set():
            self._set_status(RRCHub.STATUS_FAILED, "WELCOME timeout")
            with contextlib.suppress(Exception):
                with self._lock:
                    if self.link is not None:
                        self.link.teardown()

    def _send_hello(self, link):
        body = {
            proto.B_HELLO_NAME: proto.HELLO_CLIENT_NAME,
            proto.B_HELLO_VER: proto.HELLO_CLIENT_VERSION,
            proto.B_HELLO_CAPS: {
                proto.CAP_RESOURCE_ENVELOPE: True,
                proto.CAP_ACTION: True,
            },
        }
        env = proto.make_envelope(
            proto.T_HELLO,
            src=self.manager.identity.hash,
            body=body,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        payload = proto.encode(env)
        self._raw_send(link, payload)

    def _on_closed(self, link):
        self._stop_hello.set()
        with self._lock:
            self.link = None
            self.welcomed = False
            self.motd = None
            self.members.clear()
            self._resource_expectations.clear()
            self._pending_joins.clear()
            self._pending_parts.clear()
            self._silent_joins.clear()
            self._silent_who_rooms.clear()
            should_reconnect = self.auto_reconnect and not self._manual_disconnect
        self._set_status(RRCHub.STATUS_DISCONNECTED, "Disconnected")
        if should_reconnect:
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        with self._lock:
            self._reconnect_attempts += 1
            backoff = min(60.0, max(1.0, 2.0 ** min(self._reconnect_attempts, 6)))
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()

            self._reconnect_timer = threading.Timer(backoff, self._fire_reconnect)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()
            self._set_status(
                RRCHub.STATUS_DISCONNECTED,
                "Reconnect in " + str(int(backoff)) + "s",
            )

    def _fire_reconnect(self):
        with self._lock:
            self._reconnect_timer = None
            if self._manual_disconnect or not self.auto_reconnect:
                return
        self.connect()

    def disconnect(self):
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
            with contextlib.suppress(Exception):
                link.teardown()
        self._set_status(RRCHub.STATUS_DISCONNECTED, "Disconnected")

    def set_auto_reconnect(self, enabled, save=True):
        with self._lock:
            self.auto_reconnect = bool(enabled)
            if not enabled and self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
        if save:
            self.manager.save()
        self.manager._notify_change(self)

    def set_auto_list(self, enabled, save=True):
        with self._lock:
            self.auto_list = bool(enabled)
        if save:
            self.manager.save()
        self.manager._notify_change(self)

    def set_auto_who(self, enabled, save=True):
        with self._lock:
            self.auto_who = bool(enabled)
        if save:
            self.manager.save()
        self.manager._notify_change(self)

    def get_effective_nick(self):
        if isinstance(self.nick_override, str) and self.nick_override:
            return self.nick_override
        return self.manager.get_nickname()

    def set_nick_override(self, nick):
        with self._lock:
            if nick is None or (isinstance(nick, str) and nick == ""):
                self.nick_override = None
            else:
                self.nick_override = str(nick)
        self.manager.save()
        self.manager._notify_change(self)

    def _packet_would_fit(self, link, payload):
        try:
            pkt = RNS.Packet(link, payload)
            pkt.pack()
            return True
        except Exception:
            return False

    def _raw_send(self, link, payload):
        if isinstance(link, _LoopbackEndpoint):
            link.from_client(payload)
        else:
            RNS.Packet(link, payload).send()

    def _send_env(self, env):
        with self._lock:
            link = self.link
        if link is None or link.status != RNS.Link.ACTIVE:
            msg = "not connected"
            raise RuntimeError(msg)
        payload = proto.encode(env)
        if isinstance(link, _LoopbackEndpoint):
            link.from_client(payload)
            return
        if not self._packet_would_fit(link, payload):
            msg = "message exceeds link MTU"
            raise RuntimeError(msg)
        RNS.Packet(link, payload).send()

    def join_room(self, room, key=None, silent=False):
        r = proto.normalize_room(room)
        body = key if (isinstance(key, str) and key) else None
        env = proto.make_envelope(
            proto.T_JOIN,
            src=self.manager.identity.hash,
            room=r,
            body=body,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        with self._lock:
            self._pending_joins.add(r)
            if silent:
                self._silent_joins.add(r)
        self._send_env(env)
        with self._lock:
            if r not in self.messages:
                self.messages[r] = []
        self.manager._notify_change(self)

    def send_command(self, text, room=None, record_local=True):
        if not isinstance(text, str) or not text.startswith("/"):
            msg = "command must start with /"
            raise ValueError(msg)
        r = None
        if isinstance(room, str) and room.strip():
            r = proto.normalize_room(room)
        nick = self.get_effective_nick()
        if record_local:
            self._record_message(
                proto.RRCMessage(
                    "msg",
                    r,
                    self.manager.identity.hash,
                    nick,
                    text,
                    proto.now_ms(),
                ),
                local=True,
            )
        env = proto.make_envelope(
            proto.T_MSG,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        if nick:
            env[proto.K_NICK] = nick
        self._send_env(env)

    def send_ping(self, room=None):
        body = os.urandom(8)
        env = proto.make_envelope(
            proto.T_PING,
            src=self.manager.identity.hash,
            body=body,
        )
        with self._lock:
            now = proto.now_ms()
            self._pending_pings[body] = (now, room)
            expired = [k for k, v in self._pending_pings.items() if now - v[0] > 15000]
            for k in expired:
                self._pending_pings.pop(k, None)
        self._send_env(env)
        return body

    def part_room(self, room):
        room_n = proto.normalize_room(room)
        env = proto.make_envelope(
            proto.T_PART,
            src=self.manager.identity.hash,
            room=room_n,
        )
        with self._lock:
            self._pending_parts.add(room_n)
        with contextlib.suppress(Exception):
            self._send_env(env)
        with self._lock:
            self.rooms.discard(room_n)
        self.manager.save()
        self.manager._notify_change(self)

    def send_message(self, room, text):
        r = proto.normalize_room(room)
        if not isinstance(text, str) or not text.strip():
            msg = "message text must be non-empty"
            raise ValueError(msg)
        if len(text.encode("utf-8")) > self.max_msg_body_bytes:
            msg = "message too long for hub limit"
            raise ValueError(msg)
        env = proto.make_envelope(
            proto.T_MSG,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        mid = env[proto.K_ID]
        if isinstance(mid, (bytes, bytearray)):
            self._sent_ids.append(bytes(mid))
        self._record_message(
            proto.RRCMessage(
                "msg",
                r,
                self.manager.identity.hash,
                nick,
                text,
                proto.now_ms(),
            ),
            local=True,
        )
        self._send_env(env)
        return mid

    def send_action(self, room, text):
        r = proto.normalize_room(room)
        if not isinstance(text, str) or not text.strip():
            msg = "action text must be non-empty"
            raise ValueError(msg)
        if len(text.encode("utf-8")) > self.max_msg_body_bytes:
            msg = "action too long for hub limit"
            raise ValueError(msg)
        env = proto.make_envelope(
            proto.T_ACTION,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        mid = env[proto.K_ID]
        if isinstance(mid, (bytes, bytearray)):
            self._sent_ids.append(bytes(mid))
        self._record_message(
            proto.RRCMessage(
                "action",
                r,
                self.manager.identity.hash,
                nick,
                text,
                proto.now_ms(),
            ),
            local=True,
        )
        self._send_env(env)
        return mid

    def _per_room_cap(self):
        v = self.manager.history_per_room_cap
        try:
            v = int(v)
        except Exception:
            return None
        return v if v > 0 else None

    def _filter_history(self):
        return bool(self.manager.filter_loaded_history)

    def _ephemeral_notices_history(self):
        return self.manager.ephemeral_notices

    def _entry_for(self, msg):
        return {
            H_KIND: msg.kind,
            H_SRC: bytes(msg.src) if isinstance(msg.src, (bytes, bytearray)) else None,
            H_NICK: msg.nick if isinstance(msg.nick, str) else None,
            H_TEXT: msg.text if isinstance(msg.text, str) else "",
            H_TS: int(msg.ts) if isinstance(msg.ts, int) else proto.now_ms(),
            H_MENTION: bool(getattr(msg, "mention", False)),
        }

    def _msg_from_entry(self, room, entry):
        if not isinstance(entry, dict):
            return None
        m = proto.RRCMessage(
            entry.get(H_KIND) if isinstance(entry.get(H_KIND), str) else "msg",
            room,
            entry.get(H_SRC)
            if isinstance(entry.get(H_SRC), (bytes, bytearray))
            else None,
            entry.get(H_NICK) if isinstance(entry.get(H_NICK), str) else None,
            entry.get(H_TEXT) if isinstance(entry.get(H_TEXT), str) else "",
            entry.get(H_TS) if isinstance(entry.get(H_TS), int) else 0,
        )
        m.mention = bool(entry.get(H_MENTION, False))
        return m

    def _persistable_room(self, room):
        return isinstance(room, str) and room and room != "*"

    def _append_history(self, room, msg):
        if not self._persistable_room(room):
            return
        try:
            self.manager._ensure_history_dir(self)
            path = self.manager._history_path(self, room)
            with open(path, "ab") as f:
                f.write(proto.encode(self._entry_for(msg)))
            self._history_write_failed = False
        except Exception as e:
            if not self._history_write_failed:
                self._history_write_failed = True
                self._log(
                    "history persistence failed, suppressing further warnings "
                    "until recovery: " + str(e),
                    RNS.LOG_ERROR,
                )

    def _delete_history(self, room):
        if not self._persistable_room(room):
            return
        path = self.manager._history_path(self, room)
        with contextlib.suppress(Exception):
            if os.path.isfile(path):
                os.unlink(path)

    def _load_history(self):
        with self._lock:
            rooms = list(self.messages.keys())
        for room in rooms:
            if not self._persistable_room(room):
                continue
            path = self.manager._history_path(self, room)
            if not os.path.isfile(path):
                continue
            window = deque(maxlen=self._per_room_cap())
            decode_error = None
            try:
                with open(path, "rb") as f:
                    while True:
                        try:
                            window.append(proto.load(f))
                        except EOFError:
                            break
                        except Exception as ex:
                            decode_error = ex
                            break
            except OSError as ex:
                self._log(
                    "history load failed for #" + room + ": " + str(ex), RNS.LOG_ERROR
                )
                continue
            if decode_error is not None:
                self._log(
                    "history file for #"
                    + room
                    + " is corrupt, truncating to last "
                    + str(len(window))
                    + " valid messages: "
                    + str(decode_error),
                    RNS.LOG_ERROR,
                )
            msgs = []
            filter_msgs = self._filter_history()
            for e in window:
                m = self._msg_from_entry(room, e)
                if m is None:
                    continue
                if filter_msgs and m.kind in ("system", "notice"):
                    continue
                msgs.append(m)
            with self._lock:
                self.messages[room] = msgs

    def _clean_history(self):
        now = time.time()
        cleaned = False
        remove_after = self._ephemeral_notices_history()
        if now > self._last_history_clean + self.CLEAN_HISTORY_INTERVAL:
            with self._lock:
                try:
                    for r in self.messages:
                        old = set()
                        for m in self.messages[r]:
                            age = now - m.ts / 1000.0
                            if m.kind in ("system", "notice") and age > remove_after:
                                old.add(m)
                        for m in old:
                            self.messages[r].remove(m)
                            cleaned = True
                except Exception as e:
                    RNS.trace_exception(e)
        self._last_history_clean = time.time()
        if cleaned:
            self.clean_last_removed = time.time()

    def _record_message(self, msg, local=False):
        cap = self._per_room_cap()
        with self._lock:
            buf = self.messages.setdefault(msg.room or "*", [])
            buf.append(msg)
            if cap is not None and len(buf) > cap:
                del buf[: len(buf) - cap]
            if (
                not local
                and msg.room
                and msg.room != self.manager.active_room_for(self)
            ):
                self._bump_unread(msg.room)
                if msg.mention:
                    self.mention_rooms.add(msg.room)
            self.manager._notify_messages(self, msg)
        self._append_history(msg.room, msg)
        self._clean_history()

    def _record_system(self, room, text):
        if not room:
            return
        msg = proto.RRCMessage("system", room, None, None, text, proto.now_ms())
        cap = self._per_room_cap()
        with self._lock:
            buf = self.messages.setdefault(room, [])
            buf.append(msg)
            if cap is not None and len(buf) > cap:
                del buf[: len(buf) - cap]
            self.manager._notify_messages(self, msg)
        self._append_history(room, msg)
        self._clean_history()

    def _record_notice(self, msg):
        target_room = msg.room
        if not target_room:
            target_room = self.manager.active_room_for(self)
            if target_room:
                msg.room = target_room

        cap = self._per_room_cap()
        with self._lock:
            self.notices.append(msg)
            if len(self.notices) > 200:
                del self.notices[: len(self.notices) - 200]
            if target_room:
                buf = self.messages.setdefault(target_room, [])
                buf.append(msg)
                if cap is not None and len(buf) > cap:
                    del buf[: len(buf) - cap]
                if target_room != self.manager.active_room_for(self):
                    self._bump_unread(target_room)
            self.manager._notify_messages(self, msg)
        if target_room:
            self._append_history(target_room, msg)
            self._clean_history()

    def get_messages(self, room):
        with self._lock:
            return list(self.messages.get(room, []))

    def _on_packet(self, data):
        try:
            env = proto.decode(data)
        except Exception as e:
            self._log("decode failed: " + str(e), RNS.LOG_DEBUG)
            return
        if not isinstance(env, dict):
            return
        t = env.get(proto.K_T)

        handler = self._PACKET_HANDLERS.get(t)
        if handler is not None:
            handler(self, env)

    def _handle_ping(self, env):
        with contextlib.suppress(Exception):
            pong = proto.make_envelope(
                proto.T_PONG,
                src=self.manager.identity.hash,
                body=env.get(proto.K_BODY),
            )
            self._send_env(pong)

    def _handle_pong(self, env):
        body = env.get(proto.K_BODY)
        if not isinstance(body, (bytes, bytearray)):
            return
        key = bytes(body)
        with self._lock:
            pending = self._pending_pings.pop(key, None)
        if pending is not None:
            sent_ms, room = pending
            rtt_ms = max(0, proto.now_ms() - sent_ms)
            self._record_system(room, "Pong from hub: " + str(rtt_ms) + " ms")

    def _handle_welcome(self, env):
        self.welcomed = True
        body = env.get(proto.K_BODY)
        if isinstance(body, dict):
            hub_name = body.get(proto.B_WELCOME_HUB)
            if isinstance(hub_name, str):
                self.hub_name = hub_name
            ver = body.get(proto.B_WELCOME_VER)
            if isinstance(ver, str):
                self.hub_version = ver
            caps = body.get(proto.B_WELCOME_CAPS)
            if isinstance(caps, dict):
                self.hub_caps = dict(caps)
            limits = body.get(proto.B_WELCOME_LIMITS)
            if isinstance(limits, dict):
                self._apply_limits(limits)
        self._set_status(RRCHub.STATUS_CONNECTED, "Connected")
        with self._lock:
            self._reconnect_attempts = 0
        self.manager._on_welcome(self)
        if self.auto_list:
            try:
                with self._lock:
                    self._silent_list_pending += 1
                self.send_command("/list", room=None, record_local=False)
            except Exception:
                with self._lock:
                    if self._silent_list_pending > 0:
                        self._silent_list_pending -= 1

    def _apply_limits(self, limits):
        if proto.L_MAX_NICK_BYTES in limits:
            self.max_nick_bytes = int(limits[proto.L_MAX_NICK_BYTES])
        if proto.L_MAX_ROOM_NAME_BYTES in limits:
            self.max_room_name_bytes = int(limits[proto.L_MAX_ROOM_NAME_BYTES])
        if proto.L_MAX_MSG_BODY_BYTES in limits:
            self.max_msg_body_bytes = int(limits[proto.L_MAX_MSG_BODY_BYTES])
        if proto.L_MAX_ROOMS_PER_SESSION in limits:
            self.max_rooms_per_session = int(limits[proto.L_MAX_ROOMS_PER_SESSION])
        if proto.L_RATE_LIMIT_MSGS_PER_MINUTE in limits:
            self.rate_limit_msgs_per_minute = int(
                limits[proto.L_RATE_LIMIT_MSGS_PER_MINUTE],
            )

    def _own_hash(self):
        return self.manager.identity.hash if self.manager.identity is not None else None

    def _handle_joined(self, env):
        room = env.get(proto.K_ROOM)
        if not (isinstance(room, str) and room):
            return
        r = room.strip().lower()
        body = env.get(proto.K_BODY)
        joiner_nick = env.get(proto.K_NICK)
        own_hash = self._own_hash()

        body_hashes = []
        if isinstance(body, list):
            body_hashes = [bytes(e) for e in body if isinstance(e, (bytes, bytearray))]

        with self._lock:
            self_join = r in self._pending_joins
            silent = r in self._silent_joins
            if self_join:
                self._pending_joins.discard(r)
            if silent:
                self._silent_joins.discard(r)

            self.rooms.add(r)
            if r not in self.messages:
                self.messages[r] = []
            members = self.members.setdefault(r, set())
            for h in body_hashes:
                members.add(h)
            if own_hash is not None:
                members.add(own_hash)

            if (
                (not self_join)
                and isinstance(joiner_nick, str)
                and joiner_nick
                and len(body_hashes) == 1
            ):
                jh = body_hashes[0]
                if own_hash is None or jh != own_hash:
                    self.nicks[jh] = joiner_nick

        if self_join:
            if not silent:
                self._record_system(r, "You joined #" + r)
            if self.auto_who:
                try:
                    with self._lock:
                        self._silent_who_rooms.add(r)
                    self.send_command("/who " + r, room=r, record_local=False)
                except Exception:
                    with self._lock:
                        self._silent_who_rooms.discard(r)
            self.manager.save()
        else:
            joiner = None
            if len(body_hashes) == 1 and (
                own_hash is None or body_hashes[0] != own_hash
            ):
                joiner = body_hashes[0]
            if joiner is not None:
                self._record_system(r, self.display_name_for(joiner) + " joined")
        self.manager._notify_change(self)

    def _handle_parted(self, env):
        room = env.get(proto.K_ROOM)
        if not (isinstance(room, str) and room):
            return
        r = room.strip().lower()
        body = env.get(proto.K_BODY)
        parter_nick = env.get(proto.K_NICK)
        own_hash = self._own_hash()

        body_hashes = []
        if isinstance(body, list):
            body_hashes = [bytes(e) for e in body if isinstance(e, (bytes, bytearray))]

        with self._lock:
            self_part = r in self._pending_parts
            if self_part:
                self._pending_parts.discard(r)

            if (
                (not self_part)
                and isinstance(parter_nick, str)
                and parter_nick
                and len(body_hashes) == 1
            ):
                ph = body_hashes[0]
                if own_hash is None or ph != own_hash:
                    self.nicks[ph] = parter_nick

            members = self.members.get(r)
            if members is not None:
                for h in body_hashes:
                    members.discard(h)
            if self_part:
                self.rooms.discard(r)
                self.members.pop(r, None)

        if self_part:
            self.manager.save()
        else:
            parter = None
            if len(body_hashes) == 1 and (
                own_hash is None or body_hashes[0] != own_hash
            ):
                parter = body_hashes[0]
            if parter is not None:
                self._record_system(r, self.display_name_for(parter) + " left")
        self.manager._notify_change(self)

    def _handle_chat(self, env, kind):
        body = env.get(proto.K_BODY)
        room = env.get(proto.K_ROOM)
        src = env.get(proto.K_SRC)
        nick = env.get(proto.K_NICK)
        mid = env.get(proto.K_ID)
        own_hash = self._own_hash()
        is_own = (
            isinstance(src, (bytes, bytearray))
            and own_hash is not None
            and bytes(src) == own_hash
        )
        if (
            is_own
            and isinstance(mid, (bytes, bytearray))
            and bytes(mid) in self._sent_ids
        ):
            return
        if isinstance(src, (bytes, bytearray)) and isinstance(nick, str) and nick:
            with self._lock:
                self.nicks[bytes(src)] = nick
                if isinstance(room, str) and room:
                    self.members.setdefault(room.strip().lower(), set()).add(bytes(src))
        if not isinstance(body, str):
            return
        msg = proto.RRCMessage(
            kind,
            room.strip().lower() if isinstance(room, str) else None,
            bytes(src) if isinstance(src, (bytes, bytearray)) else None,
            nick if isinstance(nick, str) else None,
            body,
            proto.now_ms(),
        )
        if not is_own and proto.text_mentions(body, self.get_effective_nick()):
            msg.mention = True
        self._record_message(msg)

    def _handle_msg(self, env):
        self._handle_chat(env, "msg")

    def _handle_action(self, env):
        self._handle_chat(env, "action")

    def _handle_notice(self, env):
        body = env.get(proto.K_BODY)
        room = env.get(proto.K_ROOM)
        src = env.get(proto.K_SRC)
        if not isinstance(body, str):
            return

        nick_prefix = "nickname set to "
        if body.startswith(nick_prefix):
            new_nick = body[len(nick_prefix) :].strip()
            if new_nick:
                self.set_nick_override(new_nick)

        parsed = proto.parse_room_list_notice(body)
        if parsed is not None:
            with self._lock:
                self.available_rooms = parsed
                silent = self._silent_list_pending > 0
                if silent:
                    self._silent_list_pending -= 1
            self.manager._notify_change(self)
            if silent:
                return

        parsed_who = proto.parse_who_notice(body)
        if parsed_who is not None:
            who_room, who_entries = parsed_who
            with self._lock:
                members = self.members.setdefault(who_room, set())
                for nick, hash_hex in who_entries:
                    try:
                        hash_bytes = bytes.fromhex(hash_hex)
                    except Exception:
                        continue
                    if nick is None:
                        members.add(hash_bytes)
                        continue
                    for ph in members:
                        if ph.startswith(hash_bytes):
                            self.nicks[ph] = nick
                            break
                silent_who = who_room in self._silent_who_rooms
                if silent_who:
                    self._silent_who_rooms.discard(who_room)
            self.manager._notify_change(self)
            if silent_who:
                return

        room_n = room.strip().lower() if isinstance(room, str) else None
        if room_n is None and isinstance(body, str) and body.strip():
            with self._lock:
                self.motd = body
            self.manager._notify_change(self)
        msg = proto.RRCMessage(
            "notice",
            room_n,
            bytes(src) if isinstance(src, (bytes, bytearray)) else None,
            None,
            body,
            proto.now_ms(),
        )
        self._record_notice(msg)

    def _handle_error(self, env):
        body = env.get(proto.K_BODY)
        room = env.get(proto.K_ROOM)
        text = body if isinstance(body, str) else "(error)"
        r = room.strip().lower() if isinstance(room, str) else None
        rollback_join = False
        if r:
            with self._lock:
                if r in self._pending_joins:
                    rollback_join = True
                self._pending_joins.discard(r)
                self._silent_joins.discard(r)
                self._pending_parts.discard(r)
                if rollback_join:
                    self.rooms.discard(r)
            if rollback_join:
                self.manager.save()
        msg = proto.RRCMessage("error", r, None, None, text, proto.now_ms())
        self._record_notice(msg)

    def _handle_resource_envelope(self, env):
        body = env.get(proto.K_BODY)
        if not isinstance(body, dict):
            return
        with contextlib.suppress(Exception):
            rid = body.get(proto.B_RES_ID)
            kind = body.get(proto.B_RES_KIND)
            size = body.get(proto.B_RES_SIZE)
            sha256 = body.get(proto.B_RES_SHA256)
            encoding = body.get(proto.B_RES_ENCODING)
            if not isinstance(rid, (bytes, bytearray)):
                return
            if not isinstance(kind, str):
                return
            if not isinstance(size, int) or size <= 0:
                return
            room = env.get(proto.K_ROOM)
            with self._lock:
                self._resource_expectations[bytes(rid)] = {
                    "kind": kind,
                    "size": size,
                    "sha256": bytes(sha256)
                    if isinstance(sha256, (bytes, bytearray))
                    else None,
                    "encoding": encoding if isinstance(encoding, str) else "utf-8",
                    "room": room.strip().lower() if isinstance(room, str) else None,
                    "expires": time.monotonic() + 30.0,
                }

    _PACKET_HANDLERS = {
        proto.T_PING: _handle_ping,
        proto.T_PONG: _handle_pong,
        proto.T_WELCOME: _handle_welcome,
        proto.T_JOINED: _handle_joined,
        proto.T_PARTED: _handle_parted,
        proto.T_MSG: _handle_msg,
        proto.T_ACTION: _handle_action,
        proto.T_NOTICE: _handle_notice,
        proto.T_ERROR: _handle_error,
        proto.T_RESOURCE_ENVELOPE: _handle_resource_envelope,
    }

    def _resource_advertised(self, resource):
        try:
            if hasattr(resource, "get_data_size"):
                size = resource.get_data_size()
            elif hasattr(resource, "total_size"):
                size = resource.total_size
            else:
                size = getattr(resource, "size", 0)
        except Exception:
            return False
        return size <= 262144

    def _resource_concluded(self, resource):
        try:
            if resource.status != RNS.Resource.COMPLETE:
                with contextlib.suppress(Exception):
                    if hasattr(resource, "data") and resource.data:
                        resource.data.close()
                return
            data = None
            try:
                data = resource.data.read()
            finally:
                with contextlib.suppress(Exception):
                    if hasattr(resource, "data") and resource.data:
                        resource.data.close()
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
                for k in expired:
                    self._resource_expectations.pop(k, None)
                for k, exp in list(self._resource_expectations.items()):
                    if exp["size"] == len(data):
                        matched = exp
                        self._resource_expectations.pop(k, None)
                        break

            kind = matched["kind"] if matched else proto.RES_KIND_BLOB
            room = matched["room"] if matched else None
            encoding = matched["encoding"] if matched else "utf-8"
            sha = matched["sha256"] if matched else None
            if sha is not None and hashlib.sha256(data).digest() != sha:
                return
            if kind in (proto.RES_KIND_NOTICE, proto.RES_KIND_MOTD):
                try:
                    text = data.decode(encoding, errors="replace")
                except Exception:
                    return
                if kind == proto.RES_KIND_MOTD:
                    with self._lock:
                        self.motd = text
                    self.manager._notify_change(self)
                msg = proto.RRCMessage("notice", room, None, None, text, proto.now_ms())
                self._record_notice(msg)
        except Exception as e:
            self._log("resource handling failed: " + str(e), RNS.LOG_ERROR)

    def to_dict(self):
        """Return a JSON-serializable summary of this hub's state."""
        with self._lock:
            rooms = sorted(self.rooms)
            known_rooms = self.ordered_known_rooms()
            unread_counts = {k: v for k, v in self.unread_counts.items() if v > 0}
            total_unread = sum(unread_counts.values())
            return {
                "hub_hash": self.hub_hash.hex(),
                "dest_name": self.dest_name,
                "name": self.name,
                "display_name": self.get_display_name(),
                "custom_name": self.custom_name,
                "hub_icon": self.get_hub_icon(),
                "hub_name_announced": self.hub_name,
                "status": self.status,
                "status_text": self.status_text,
                "connected": self.status == RRCHub.STATUS_CONNECTED,
                "hub_name": self.hub_name,
                "hub_version": self.hub_version,
                "motd": self.motd,
                "rooms": rooms,
                "known_rooms": known_rooms,
                "unread_rooms": sorted(self.unread_rooms),
                "unread_counts": unread_counts,
                "total_unread": total_unread,
                "mention_rooms": sorted(self.mention_rooms),
                "available_rooms": dict(self.available_rooms),
                "auto_reconnect": bool(self.auto_reconnect),
                "auto_list": bool(self.auto_list),
                "auto_who": bool(self.auto_who),
                "nick_override": self.nick_override,
                "max_msg_body_bytes": self.max_msg_body_bytes,
            }

    def room_messages(self, room):
        """Return serialized messages for a room."""
        return [m.to_dict() for m in self.get_messages(proto.normalize_room(room))]

    def members_dict(self, room):
        """Return serialized members for a room."""
        r = proto.normalize_room(room)
        out = []
        for h in self.get_members(r):
            out.append({"hash": h.hex(), "name": self.display_name_for(h)})
        out.sort(key=lambda m: m["name"].lower())
        return out


class RRCManager:
    """Owns the set of configured RRC hubs and relays their events."""

    def __init__(
        self,
        identity,
        storage_dir,
        get_nickname=None,
        get_name_for_identity_hash=None,
        history_per_room_cap=0,
        filter_loaded_history=True,
        ephemeral_notices=RRCHub.SYS_NOTICE_TIMEOUT,
    ):
        self.identity = identity
        self.storage_dir = storage_dir
        self._get_nickname = get_nickname
        self.get_name_for_identity_hash = get_name_for_identity_hash
        self.history_per_room_cap = history_per_room_cap
        self.filter_loaded_history = filter_loaded_history
        self.ephemeral_notices = ephemeral_notices

        self.hubs = []
        self._server_manager = None
        self._lock = threading.RLock()
        self._change_callback = None
        self._message_callback = None
        self._active_hub = None
        self._active_room = None
        self._loaded = False
        self._loading = False
        self._save_lock = threading.Lock()

    def get_nickname(self):
        if self._get_nickname is None:
            return None
        try:
            n = self._get_nickname()
        except Exception:
            return None
        return n if isinstance(n, str) and n else None

    def set_server_manager(self, server_manager):
        self._server_manager = server_manager

    def find_local_server(self, hub_hash):
        """Return a running locally hosted hub matching ``hub_hash``, if any."""
        sm = self._server_manager
        if sm is None:
            return None
        with contextlib.suppress(Exception):
            for hub in list(sm.hubs):
                if hub.running and hub.dest_hash == hub_hash:
                    return hub
        return None

    def set_change_callback(self, cb):
        self._change_callback = cb

    def set_message_callback(self, cb):
        self._message_callback = cb

    def _notify_change(self, hub=None):
        with contextlib.suppress(Exception):
            if self._change_callback is not None:
                self._change_callback(hub)

    def _notify_messages(self, hub, msg):
        with contextlib.suppress(Exception):
            if self._message_callback is not None:
                self._message_callback(hub, msg)

    def _on_welcome(self, hub):
        for r in list(hub.rooms):
            with contextlib.suppress(Exception):
                hub.join_room(r, silent=True)

    def set_active(self, hub, room):
        self._active_hub = hub
        self._active_room = room
        if hub is not None and room is not None:
            hub.mark_read(room)

    def active_room_for(self, hub):
        if self._active_hub is hub:
            return self._active_room
        return None

    def has_unread(self):
        with self._lock:
            return any(hub.unread_rooms for hub in self.hubs)

    def add_hub(self, hub_hash, dest_name=None, name=None):
        with self._lock:
            for h in self.hubs:
                if h.hub_hash == hub_hash and h.dest_name == (
                    dest_name or proto.DEFAULT_DEST_NAME
                ):
                    return h
            hub = RRCHub(self, hub_hash, dest_name=dest_name, name=name)
            self.hubs.append(hub)
        self.save()
        self._notify_change()
        return hub

    def remove_hub(self, hub):
        with self._lock:
            if hub in self.hubs:
                self.hubs.remove(hub)
        with contextlib.suppress(Exception):
            hub.disconnect()
        self.save()
        self._notify_change()

    def find_hub(self, hub_hash, dest_name=None):
        dn = dest_name or proto.DEFAULT_DEST_NAME
        with self._lock:
            for h in self.hubs:
                if h.hub_hash == hub_hash and h.dest_name == dn:
                    return h
        return None

    def find_hub_by_hex(self, hub_hash_hex, dest_name=None):
        try:
            hub_hash = bytes.fromhex(hub_hash_hex)
        except (ValueError, TypeError):
            return None
        if dest_name is not None:
            return self.find_hub(hub_hash, dest_name=dest_name)
        with self._lock:
            for h in self.hubs:
                if h.hub_hash == hub_hash:
                    return h
        return None

    def _store_path(self):
        return os.path.join(self.storage_dir, "rrc_hubs")

    def _history_root(self):
        return os.path.join(self.storage_dir, HISTORY_DIR_NAME)

    def _history_dir(self, hub):
        hub_key = hub.hub_hash.hex()
        if hub.dest_name and hub.dest_name != proto.DEFAULT_DEST_NAME:
            suffix = hashlib.sha256(hub.dest_name.encode("utf-8")).hexdigest()[:8]
            hub_key = hub_key + "__" + suffix
        return os.path.join(self._history_root(), hub_key)

    def _history_path(self, hub, room):
        sanitized = HISTORY_FILENAME_SANITIZE_RE.sub("_", room or "")[:64]
        room_hash = hashlib.sha256((room or "").encode("utf-8")).hexdigest()[:8]
        if sanitized:
            filename = sanitized + "_" + room_hash + ".log"
        else:
            filename = room_hash + ".log"
        return os.path.join(self._history_dir(hub), filename)

    def _ensure_history_dir(self, hub):
        d = self._history_dir(hub)
        os.makedirs(d, exist_ok=True)
        return d

    def load(self):
        if self._loaded:
            return
        self._loaded = True
        path = self._store_path()
        if not os.path.isfile(path):
            return
        self._loading = True
        try:
            with open(path, "rb") as f:
                data = f.read()
            obj = proto.decode(data)
            if not isinstance(obj, dict):
                return
            entries = obj.get("hubs")
            if not isinstance(entries, list):
                return
            for e in entries:
                self._load_hub_entry(e)
        except Exception as e:
            RNS.log("Failed to load RRC hubs: " + str(e), RNS.LOG_ERROR)
        finally:
            self._loading = False

    def connect_auto_reconnect_hubs(self):
        """Connect hubs that have auto-reconnect enabled (e.g. after startup load)."""
        with self._lock:
            hubs = [h for h in self.hubs if h.auto_reconnect]
        for hub in hubs:
            with hub._lock:
                if hub.status in (
                    RRCHub.STATUS_CONNECTING,
                    RRCHub.STATUS_CONNECTED,
                ):
                    continue
            hub.connect()

    def _load_hub_entry(self, e):
        if not isinstance(e, dict):
            return
        hh = e.get("hash")
        if not isinstance(hh, (bytes, bytearray)):
            return
        dn = e.get("dest_name")
        nm = e.get("name")
        hub = self.add_hub(
            bytes(hh),
            dest_name=dn if isinstance(dn, str) else None,
            name=nm if isinstance(nm, str) else None,
        )
        rooms = e.get("rooms")
        if isinstance(rooms, list):
            for r in rooms:
                if isinstance(r, str):
                    hub.add_room(r)
        parted = e.get("parted_rooms")
        if isinstance(parted, list):
            for r in parted:
                if isinstance(r, str):
                    with contextlib.suppress(Exception):
                        rn = proto.normalize_room(r)
                        with hub._lock:
                            hub.messages.setdefault(rn, [])
        cn = e.get("custom_name")
        if isinstance(cn, str) and cn.strip():
            hub.custom_name = cn.strip()
        hi = e.get("hub_icon")
        if isinstance(hi, str) and hi.strip():
            with contextlib.suppress(ValueError):
                hub.set_hub_icon(hi.strip(), save=False)
        ro = e.get("room_order")
        if isinstance(ro, list):
            cleaned = []
            for r in ro:
                if isinstance(r, str) and r.strip():
                    with contextlib.suppress(ValueError):
                        cleaned.append(proto.normalize_room(r))
            hub.room_order = cleaned
        ar = e.get("auto_reconnect")
        if isinstance(ar, bool):
            hub.auto_reconnect = ar
        elif ar is None:
            hub.auto_reconnect = True
        al = e.get("auto_list")
        if isinstance(al, bool):
            hub.auto_list = al
        aw = e.get("auto_who")
        if isinstance(aw, bool):
            hub.auto_who = aw
        no = e.get("nick")
        if isinstance(no, str) and no:
            hub.nick_override = no
        try:
            hub._load_history()
        except Exception as ex:
            RNS.log(
                "Failed to load RRC history for " + hub.name + ": " + str(ex),
                RNS.LOG_ERROR,
            )

    def save(self):
        if self._loading:
            return
        path = self._store_path()
        tmp_path = path + ".tmp"
        with self._save_lock:
            try:
                entries = []
                with self._lock:
                    for h in self.hubs:
                        entries.append(self._hub_entry(h))
                data = proto.encode({"hubs": entries})
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(tmp_path, "wb") as f:
                    f.write(data)
                    f.flush()
                    with contextlib.suppress(Exception):
                        os.fsync(f.fileno())
                os.replace(tmp_path, path)
            except Exception:
                with contextlib.suppress(Exception):
                    os.unlink(tmp_path)

    def _hub_entry(self, h):
        joined = set(h.rooms)
        parted = set(h.messages.keys()) - joined
        entry = {
            "hash": h.hub_hash,
            "dest_name": h.dest_name,
            "name": h.name,
            "rooms": sorted(joined),
            "parted_rooms": sorted(parted),
            "auto_reconnect": bool(h.auto_reconnect),
            "auto_list": bool(h.auto_list),
            "auto_who": bool(h.auto_who),
        }
        if isinstance(h.nick_override, str) and h.nick_override:
            entry["nick"] = h.nick_override
        if isinstance(h.custom_name, str) and h.custom_name:
            entry["custom_name"] = h.custom_name
        icon = h.get_hub_icon()
        if icon:
            entry["hub_icon"] = icon
        if h.room_order:
            entry["room_order"] = list(h.room_order)
        return entry

    def reorder_hubs(self, hub_hashes):
        if not isinstance(hub_hashes, list):
            return False
        order = []
        for hh in hub_hashes:
            if not isinstance(hh, str):
                continue
            hub = self.find_hub_by_hex(hh.strip())
            if hub is not None:
                order.append(hub)
        with self._lock:
            remaining = [h for h in self.hubs if h not in order]
            self.hubs = order + remaining
        self.save()
        self._notify_change()
        return True

    def to_dict(self):
        """Return a JSON-serializable summary of all configured hubs."""
        with self._lock:
            hubs = list(self.hubs)
        return {"hubs": [h.to_dict() for h in hubs]}

    def shutdown(self):
        for h in list(self.hubs):
            with contextlib.suppress(Exception):
                h.disconnect()
