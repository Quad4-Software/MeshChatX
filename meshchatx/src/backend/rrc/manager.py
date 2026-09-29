# SPDX-License-Identifier: 0BSD

"""Reticulum Relay Chat session management.

Contains RRCHub, which owns the Reticulum link and protocol state for a
single hub, and RRCManager, which tracks the set of configured hubs,
persists them, and relays change and message notifications to the application.
"""

import bisect
import contextlib
import hashlib
import os
import random
import re
import threading
import time
from collections import deque
from typing import ClassVar

import RNS

from meshchatx.src.backend.path_utils import (
    path_response_window,
    slowest_online_bitrate,
)
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.room_key_crypto import decrypt_room_key, encrypt_room_key
from meshchatx.src.backend.rrc.server import _LoopbackEndpoint
from meshchatx.src.path_utils import atomic_write_bytes

DEFAULT_DEST_NAME = proto.DEFAULT_DEST_NAME
SLOW_CHANNEL_BPS = 300
_slow_connect_gate = threading.Semaphore(1)

# Auto-reconnect backoff: starts at RECONNECT_BACKOFF_BASE_S, doubles per
# failed attempt, and is capped at RECONNECT_BACKOFF_MAX_S with a random
# jitter so large hub sets do not retry in lockstep.
RECONNECT_BACKOFF_BASE_S = 2.0
RECONNECT_BACKOFF_MAX_S = 900.0
RECONNECT_BACKOFF_JITTER = 0.25

# A hub announce proves the hub is alive, so it is worth retrying soon.
# Announce-driven backoff resets are rate limited per hub so an announcing
# but unreachable hub cannot pin the reconnect loop at the fastest tier.
ANNOUNCE_RESET_MIN_INTERVAL_S = 300.0

# Minimum interval between path requests sent to the same hub during
# connect attempts.
# Minimum seconds between path requests emitted by connect workers. Doubles
# as the cross-attempt dedup window and the in-window retry cadence: a single
# request on cold air stalls a connect, while 60s was far too coarse for a
# retry to matter inside one attempt window.
CONNECT_PATH_RETRY_S = 5.0
# Upper bound for a link stuck in PENDING during connect. RNS's own
# establishment timeout can run several minutes on a dead path, which
# leaves the hub parked in CONNECTING with no forward progress.
CONNECT_LINK_WATCHDOG_S = 60.0

# Delay between auto-connect starts so a large configured hub set does
# not burst link requests at startup.
AUTO_CONNECT_STAGGER_S = 0.25


def _format_reconnect_delay(seconds):
    if seconds >= 120:
        return str(round(seconds / 60)) + "m"
    return str(int(seconds)) + "s"


BAD_KEY_MARKERS = ("bad key (+k)", "bad key")
FORCED_LEAVE_MARKERS = ("kicked from", "banned from", "banned (kline)")
JOIN_FATAL_MARKERS = ("banned from", "bad key", "invite-only")

HISTORY_DIR_NAME = "rrc_history"
HISTORY_FILENAME_SANITIZE_RE = re.compile(r"[^a-z0-9._-]+")

H_KIND = "k"
H_SRC = "s"
H_NICK = "n"
H_TEXT = "t"
H_TS = "ts"
H_MENTION = "m"
H_EVENT = "e"
H_DELIVERY = "d"

# Own messages are confirmed when the hub relays the echo back. Links are
# reliable transport, so a missing echo past this window means the hub
# dropped it (rate limit, crash) or the link is silently wedged.
DELIVERY_TIMEOUT_S = 15.0


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
        self._expected_closed_link = None
        self.status = RRCHub.STATUS_DISCONNECTED
        self.status_text = "Disconnected"
        self.welcomed = False
        self.hub_name = None
        self._hub_identity_hash = None
        self.hub_version = None
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
        self.auto_list = True
        self.auto_who = False

        self._lock = threading.RLock()
        self._resource_expectations = {}
        self._sent_ids = deque(maxlen=256)

        self._hello_thread = None
        self._stop_hello = threading.Event()
        self._manual_disconnect = False
        self._reconnect_attempts = 0
        self._reconnect_timer = None
        self._last_announce_reset = float("-inf")
        self._last_path_request = float("-inf")
        self._had_session = False
        # Envelope id -> (message, sent monotonic). Echo-confirmed, timed out,
        # or flushed failed on link loss.
        self._pending_delivery = {}
        self._last_history_clean = 0

        self.available_rooms = {}
        self.available_keyed_rooms = []
        self._silent_list_pending = 0
        self._silent_list_deadline = 0.0
        self._silent_who_rooms = set()
        self._silent_who_ts = {}

        self.nick_override = None
        self._pending_joins = set()
        self._pending_parts = set()
        self._silent_joins = set()

        self._history_write_failed = False
        self._seq_counter = 0

    def _next_seq(self):
        with self._lock:
            self._seq_counter += 1
            return self._seq_counter

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
            ordered.extend(sorted(known - seen))
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

    def connect(self, reset_attempts=True):
        """Start a connect attempt.

        A user or policy driven connect clears the retry counter so a hub
        that decayed to a slow backoff retries immediately. Timer driven
        reconnects call this with reset_attempts=False so the backoff can
        keep growing across consecutive failures.
        """
        with self._lock:
            if self.status in (RRCHub.STATUS_CONNECTING, RRCHub.STATUS_CONNECTED):
                return
            self._manual_disconnect = False
            if reset_attempts:
                self._reconnect_attempts = 0
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
            if self._reconnect_attempts > 0:
                text = "Reconnecting (attempt " + str(self._reconnect_attempts) + ")"
            else:
                text = "Connecting"
            self._connect_epoch = getattr(self, "_connect_epoch", 0) + 1
            epoch = self._connect_epoch
            self._set_status(RRCHub.STATUS_CONNECTING, text)

        t = threading.Thread(
            target=self._connect_worker,
            args=(epoch,),
            daemon=True,
        )
        t.start()

    def note_hub_announce(self):
        """Handle a fresh announce for this hub.

        An announce proves the hub is still on the network, so decayed
        backoff is reset and a pending slow retry is brought forward. The
        reset is rate limited so a hub that announces regularly while its
        listener is down cannot hold the backoff at the fastest tier.
        """
        with self._lock:
            if self.status in (RRCHub.STATUS_CONNECTING, RRCHub.STATUS_CONNECTED):
                return
            if self._manual_disconnect or not self.auto_reconnect:
                return
            if self._reconnect_attempts <= 0:
                return
            now = time.monotonic()
            if now - self._last_announce_reset < ANNOUNCE_RESET_MIN_INTERVAL_S:
                return
            self._last_announce_reset = now
            self._reconnect_attempts = 0
            reschedule = self._reconnect_timer is not None
        if reschedule:
            self._schedule_reconnect()

    def _connect_loopback(self, server):
        self._stop_hello.clear()
        link = _LoopbackEndpoint(self, server)
        server._attach_loopback(link, self.manager.identity)
        with self._lock:
            self._hub_identity_hash = server.identity.hash
            self._expected_closed_link = None
            self.link = link
        self._set_status(RRCHub.STATUS_CONNECTING, "Connected locally, sending HELLO")
        self._hello_thread = threading.Thread(target=self._hello_loop, daemon=True)
        self._hello_thread.start()

    def _connect_worker(self, epoch=None):
        try:
            server = self.manager.find_local_server(self.hub_hash)
            if server is not None:
                self._connect_loopback(server)
                return

            timeout_s = 20.0
            bitrate = slowest_online_bitrate()
            gate = (
                _slow_connect_gate
                if bitrate is not None and bitrate < SLOW_CHANNEL_BPS
                else None
            )
            if gate is not None:
                gate.acquire()
            try:
                path_wait = timeout_s
                if not RNS.Transport.has_path(self.hub_hash):
                    try:
                        path_wait = path_response_window(self.hub_hash)
                    except Exception:
                        path_wait = float(RNS.Transport.PATH_REQUEST_TIMEOUT)

                # A single deadline covers both the path response and the
                # identity recall: the announce that creates the path also
                # delivers the identity. Both must be present before the
                # link is created - RNS.Link sends the link request exactly
                # once, so a link created with no known path is dropped on
                # the floor and stalls until its establishment timeout.
                hub_identity = None
                deadline = time.monotonic() + path_wait
                while time.monotonic() < deadline:
                    hub_identity = RNS.Identity.recall(self.hub_hash)
                    if hub_identity is not None and RNS.Transport.has_path(
                        self.hub_hash
                    ):
                        break
                    hub_identity = None
                    now_m = time.monotonic()
                    if not RNS.Transport.has_path(self.hub_hash) and (
                        now_m - self._last_path_request >= CONNECT_PATH_RETRY_S
                    ):
                        # Retry the request inside the connect window: the
                        # first packet can go out before an interface is
                        # fully online, and a single dropped request would
                        # otherwise stall the whole window. The cadence cap
                        # doubles as the dedup for back-to-back attempts.
                        self._last_path_request = now_m
                        RNS.Transport.request_path(self.hub_hash)
                    time.sleep(0.2)
            finally:
                if gate is not None:
                    gate.release()

            if self._manual_disconnect:
                # disconnect() ran during the path/identity wait window:
                # do not create the link the user already asked to cancel.
                self._set_status(RRCHub.STATUS_DISCONNECTED, "Disconnected")
                return
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

            with self._lock:
                self._hub_identity_hash = hub_identity.hash

            self._stop_hello.clear()
            link = RNS.Link(
                hub_dest,
                established_callback=self._on_established,
                closed_callback=self._on_closed,
            )
            link.set_packet_callback(lambda data, pkt: self._on_packet(data))
            with self._lock:
                if epoch is not None and epoch != self._connect_epoch:
                    # A newer connect() already owns the session: drop this
                    # attempt's link instead of racing two live links.
                    with contextlib.suppress(Exception):
                        link.teardown()
                    return
                self._expected_closed_link = None
                self.link = link

            # Bound the establishment phase: a link stuck PENDING on a dead
            # path sits in CONNECTING until RNS's multi-minute timeout. Give
            # up sooner and let reconnect backoff retry instead.
            def _establish_watchdog():
                try:
                    bound = max(
                        CONNECT_LINK_WATCHDOG_S,
                        path_response_window(self.hub_hash),
                    )
                except Exception:
                    bound = CONNECT_LINK_WATCHDOG_S
                deadline = time.monotonic() + bound
                while time.monotonic() < deadline:
                    if link.status != RNS.Link.PENDING:
                        return
                    if self._stop_hello.is_set():
                        return
                    time.sleep(0.5)
                if link.status == RNS.Link.PENDING:
                    with self._lock:
                        if self.link is not link:
                            return
                        self._expected_closed_link = link
                    with contextlib.suppress(Exception):
                        link.teardown()
                    self._set_status(
                        RRCHub.STATUS_FAILED,
                        "Link establishment timed out",
                    )
                    self._maybe_schedule_reconnect_after_failed_connect()

            watchdog = threading.Thread(target=_establish_watchdog, daemon=True)
            watchdog.start()
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
                if self.status == RRCHub.STATUS_CONNECTING:
                    self._on_closed(cur_link)
                return
            try:
                self._send_hello(cur_link)
            except Exception as e:
                self._log("HELLO send failed: " + str(e), RNS.LOG_ERROR)
            attempts += 1
            self._stop_hello.wait(timeout=3.0)
        if not self.welcomed and not self._stop_hello.is_set():
            self._fail_welcome_timeout()

    def _fail_welcome_timeout(self):
        self._set_status(RRCHub.STATUS_FAILED, "WELCOME timeout")
        with self._lock:
            link = self.link
            # The teardown callback may arrive later; mark it expected so
            # _on_closed does not double-count this failure in the backoff.
            self._expected_closed_link = link
        if link is not None:
            with contextlib.suppress(Exception):
                link.teardown()
        with self._lock:
            if self.link is link:
                self.link = None
        if self.status == RRCHub.STATUS_FAILED:
            self._maybe_schedule_reconnect_after_failed_connect()

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
            if getattr(self, "_last_closed_link", None) is link:
                # Same dead link delivered twice (watchdog teardown after
                # RNS already reported the close, or a second teardown):
                # everything below must run once per link.
                return
            if self.link is not None and link is not self.link:
                # A stale teardown callback (late watchdog close or a racing
                # reconnect) must not tear down the current live session.
                return
            self._last_closed_link = link
            was_welcomed = self.welcomed
            rooms = list(self.rooms)
            manual = self._manual_disconnect
            self.link = None
            self.welcomed = False
            self.motd = None
            self.members.clear()
            self._resource_expectations.clear()
            self._pending_joins.clear()
            self._pending_parts.clear()
            flushed = self._flush_pending_delivery_locked()
            self._silent_joins.clear()
            self._silent_who_rooms.clear()
            self._silent_who_ts.clear()
            self.nicks.clear()
            expected = link is getattr(self, "_expected_closed_link", None)
            if expected:
                self._expected_closed_link = None
            should_reconnect = (
                self.auto_reconnect and not self._manual_disconnect and not expected
            )
        if was_welcomed and rooms:
            text = "Disconnected from hub" if manual else "Connection lost"
            self._record_connection_event(text, rooms=rooms)
        for msg in flushed:
            self.manager._notify_messages(self, msg)
        self._set_status(RRCHub.STATUS_DISCONNECTED, "Disconnected")
        if should_reconnect:
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        with self._lock:
            self._reconnect_attempts += 1
            backoff = min(
                RECONNECT_BACKOFF_MAX_S,
                RECONNECT_BACKOFF_BASE_S ** min(self._reconnect_attempts, 12),
            )
            backoff += random.uniform(  # noqa: S311 - retry jitter, not crypto
                0.0,
                backoff * RECONNECT_BACKOFF_JITTER,
            )
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()

            self._reconnect_timer = threading.Timer(backoff, self._fire_reconnect)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()
            self._set_status(
                RRCHub.STATUS_DISCONNECTED,
                "Reconnect in " + _format_reconnect_delay(backoff),
            )

    def _fire_reconnect(self):
        with self._lock:
            self._reconnect_timer = None
            if self._manual_disconnect or not self.auto_reconnect:
                return
        self.connect(reset_attempts=False)

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
            should_list = self.auto_list and self.welcomed
        if save:
            self.manager.save()
        self.manager._notify_change(self)
        if should_list:
            self._request_room_list()

    def request_room_list(self):
        """Request a fresh public room list from the hub (/list).

        The hub reply replaces available_rooms (adds new rooms and drops
        removed ones). The list notice is silent so it does not appear in
        chat history.
        """
        with self._lock:
            now = time.monotonic()
            if now > self._silent_list_deadline:
                self._silent_list_pending = 0
            self._silent_list_pending += 1
            self._silent_list_deadline = now + 60.0
        try:
            self.send_command("/list", room=None, record_local=False)
        except Exception:
            with self._lock:
                if self._silent_list_pending > 0:
                    self._silent_list_pending -= 1
            raise

    def _request_room_list(self):
        with contextlib.suppress(Exception):
            self.request_room_list()

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

    def _send_env_then_maybe_record(self, env, local_msg):
        """Send on the wire, then record local history if send succeeded.

        Mesh send is async, so the local echo still lands before a remote
        reply. Loopback delivery is synchronous, so the echo is recorded
        first or the hub notice would appear above the typed command.
        """
        with self._lock:
            link = self.link
            loopback = isinstance(link, _LoopbackEndpoint)
        if link is None or link.status != RNS.Link.ACTIVE:
            msg = "not connected"
            raise RuntimeError(msg)
        if local_msg is not None and loopback:
            self._record_message(local_msg, local=True)
        self._send_env(env)
        if local_msg is not None and not loopback:
            self._record_message(local_msg, local=True)

    def join_room(self, room, key=None, silent=False):
        r = proto.normalize_room(room)
        body = None
        if isinstance(key, str):
            stripped = key.strip()
            if stripped:
                body = stripped
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
        try:
            self._send_env(env)
        except Exception:
            with self._lock:
                self._pending_joins.discard(r)
                self._silent_joins.discard(r)
            raise
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
        env = proto.make_envelope(
            proto.T_MSG,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        if nick:
            env[proto.K_NICK] = nick
        local_msg = None
        if record_local:
            local_msg = proto.RRCMessage(
                "msg",
                r,
                self.manager.identity.hash,
                nick,
                self._redact_command_for_history(text),
                proto.now_ms(),
            )
        self._send_env_then_maybe_record(env, local_msg)

    @staticmethod
    def _redact_command_for_history(text):
        """Omit +k secrets from locally recorded command history."""
        parts = text.split()
        if len(parts) >= 4 and parts[0].lower() == "/mode" and parts[2].lower() == "+k":
            return " ".join([*parts[:3], "***"])
        return text

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
            self.messages.pop(room_n, None)
            self.unread_rooms.discard(room_n)
            self.unread_counts.pop(room_n, None)
            self.mention_rooms.discard(room_n)
            self.members.pop(room_n, None)
        self._delete_history(room_n)
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
        local_msg = proto.RRCMessage(
            "msg",
            r,
            self.manager.identity.hash,
            nick,
            text,
            proto.now_ms(),
        )
        self._track_outbound(local_msg, mid)
        try:
            self._send_env_then_maybe_record(env, local_msg)
        except Exception:
            self._untrack_outbound(local_msg)
            raise
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
        local_msg = proto.RRCMessage(
            "action",
            r,
            self.manager.identity.hash,
            nick,
            text,
            proto.now_ms(),
        )
        self._track_outbound(local_msg, mid)
        try:
            self._send_env_then_maybe_record(env, local_msg)
        except Exception:
            self._untrack_outbound(local_msg)
            raise
        return mid

    def _track_outbound(self, local_msg, mid):
        """Mark a locally sent message as pending hub echo confirmation."""
        if isinstance(mid, (bytes, bytearray)):
            mid = bytes(mid)
            local_msg.mid = mid
            local_msg.delivery = "sending"
            with self._lock:
                self._sent_ids.append(mid)
                self._pending_delivery[mid] = (local_msg, time.monotonic())
                stale = []
                while len(self._pending_delivery) > 256:
                    stale_mid, (stale_msg, _t) = next(
                        iter(self._pending_delivery.items())
                    )
                    stale_msg.delivery = "failed"
                    stale.append(stale_msg)
                    del self._pending_delivery[stale_mid]
            for stale_msg in stale:
                self.manager._notify_messages(self, stale_msg)

    def _untrack_outbound(self, local_msg):
        """Send raised before recording; drop the pending echo marker."""
        mid = getattr(local_msg, "mid", None)
        local_msg.delivery = None
        if isinstance(mid, (bytes, bytearray)):
            with self._lock:
                self._pending_delivery.pop(bytes(mid), None)

    def _sweep_pending_delivery(self):
        """Flag pending own messages whose hub echo never arrived."""
        expired = []
        now = time.monotonic()
        with self._lock:
            for mid, (msg, sent_at) in list(self._pending_delivery.items()):
                if now - sent_at >= DELIVERY_TIMEOUT_S:
                    msg.delivery = "failed"
                    expired.append(msg)
                    del self._pending_delivery[mid]
        for msg in expired:
            self.manager._notify_messages(self, msg)

    def _flush_pending_delivery_locked(self):
        """Link is gone: every unconfirmed send is marked failed."""
        failed = [msg for msg, _t in self._pending_delivery.values()]
        self._pending_delivery.clear()
        # Notifications fire outside the lock by the caller on a snapshot.
        for msg in failed:
            msg.delivery = "failed"
        return failed

    def _confirm_delivery(self, mid):
        msg = None
        with self._lock:
            entry = self._pending_delivery.pop(mid, None)
            if entry is not None:
                msg = entry[0]
                msg.delivery = "sent"
        if msg is not None:
            self.manager._notify_messages(self, msg)

    def retry_message(self, room, seq):
        """Resend an own message that failed delivery. Returns the new mid."""
        room = proto.normalize_room(room)
        msg = None
        with self._lock:
            for m in self.messages.get(room, []):
                if m.seq == seq:
                    msg = m
                    break
        if msg is None:
            raise ValueError(f"no message with seq {seq}")
        if msg.delivery != "failed":
            raise ValueError("only failed messages can be retried")
        if msg.kind == "action":
            env = proto.make_envelope(
                proto.T_ACTION,
                src=self.manager.identity.hash,
                room=room,
                body=msg.text,
            )
        else:
            env = proto.make_envelope(
                proto.T_MSG,
                src=self.manager.identity.hash,
                room=room,
                body=msg.text,
            )
        nick = msg.nick or self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        mid = env[proto.K_ID]
        with self._lock:
            if isinstance(msg.mid, (bytes, bytearray)):
                self._pending_delivery.pop(bytes(msg.mid), None)
        mid_b = None
        if isinstance(mid, (bytes, bytearray)):
            mid_b = bytes(mid)
            with self._lock:
                msg.mid = mid_b
                msg.delivery = "sending"
                self._sent_ids.append(mid_b)
                self._pending_delivery[mid_b] = (msg, time.monotonic())
        try:
            self._send_env(env)
        except Exception:
            if mid_b is not None:
                with self._lock:
                    self._pending_delivery.pop(mid_b, None)
            msg.delivery = "failed"
            raise
        self.manager._notify_messages(self, msg)
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
            H_EVENT: getattr(msg, "event", None),
            H_DELIVERY: getattr(msg, "delivery", None),
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
        event = entry.get(H_EVENT)
        m.event = event if isinstance(event, str) and event else None
        delivery = entry.get(H_DELIVERY)
        if delivery in ("sent", "failed"):
            m.delivery = delivery
        elif delivery == "sending":
            # History only survives across sessions; anything still pending at
            # load can never be confirmed by this connection.
            m.delivery = "failed"
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
                    data = f.read()
                pos = 0
                size = len(data)
                while pos < size:
                    start = pos
                    try:
                        entry, pos = proto.decode_item(data, pos)
                    except Exception as ex:
                        decode_error = ex
                        pos = start + 1
                    else:
                        window.append(entry)
            except OSError as ex:
                self._log(
                    "history load failed for #" + room + ": " + str(ex),
                    RNS.LOG_ERROR,
                )
                continue
            if decode_error is not None:
                self._log(
                    "history file for #"
                    + room
                    + " has a corrupt record, kept "
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
                m.seq = self._next_seq()
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
            self._compact_history_files()

    HISTORY_FILE_MAX_BYTES = 8 * 1024 * 1024

    def _compact_history_files(self):
        with self._lock:
            rooms = list(self.messages.keys())
        for room in rooms:
            if not self._persistable_room(room):
                continue
            path = self.manager._history_path(self, room)
            try:
                if os.path.getsize(path) <= self.HISTORY_FILE_MAX_BYTES:
                    continue
            except OSError:
                continue
            try:
                with self._lock:
                    msgs = list(self.messages.get(room, []))
                entries = [
                    self._entry_for(m)
                    for m in msgs
                    if isinstance(m, proto.RRCMessage)
                ]
                from meshchatx.src.path_utils import atomic_write_bytes

                atomic_write_bytes(
                    path,
                    b"".join(proto.encode(e) for e in entries),
                )
                self._log(
                    "compacted history for #" + room,
                    RNS.LOG_DEBUG,
                )
            except Exception as e:
                self._log(
                    "history compaction failed for #" + room + ": " + str(e),
                    RNS.LOG_ERROR,
                )

    def _record_message(self, msg, local=False):
        cap = self._per_room_cap()
        with self._lock:
            msg.seq = self._next_seq()
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

    def _record_system(self, room, text, event=None):
        if not room:
            return
        msg = proto.RRCMessage("system", room, None, None, text, proto.now_ms())
        msg.event = event if isinstance(event, str) and event else None
        cap = self._per_room_cap()
        with self._lock:
            msg.seq = self._next_seq()
            buf = self.messages.setdefault(room, [])
            buf.append(msg)
            if cap is not None and len(buf) > cap:
                del buf[: len(buf) - cap]
            self.manager._notify_messages(self, msg)
        self._append_history(room, msg)
        self._clean_history()

    def _record_connection_event(self, text, rooms=None):
        """Write a connection status line into each joined room timeline."""
        if rooms is None:
            with self._lock:
                rooms = list(self.rooms)
        for room in rooms:
            with contextlib.suppress(Exception):
                self._record_system(room, text)

    def _record_notice(self, msg):
        target_room = msg.room
        if not target_room:
            target_room = self.manager.active_room_for(self)
            if target_room:
                msg.room = target_room

        cap = self._per_room_cap()
        with self._lock:
            msg.seq = self._next_seq()
            self.notices.append(msg)
            if len(self.notices) > 200:
                del self.notices[: len(self.notices) - 200]
            if target_room:
                buf = self.messages.setdefault(target_room, [])
                buf.append(msg)
                if cap is not None and len(buf) > cap:
                    del buf[: len(buf) - cap]
                if target_room != self.manager.active_room_for(self):
                    # Informational notices (MOTD, WHO replies, room lists, and
                    # join/part chatter on hubs that send it as NOTICE) must not
                    # light the unread badge. Errors still do, so kicks and bad
                    # keys surface. After kick/rollback the room is already
                    # removed from self.rooms, so guard on membership.
                    if msg.kind == "error" and target_room in self.rooms:
                        self._bump_unread(target_room)
            self.manager._notify_messages(self, msg)
        if target_room:
            self._append_history(target_room, msg)
            self._clean_history()

    def get_messages(self, room):
        with self._lock:
            return list(self.messages.get(room, []))

    def _on_packet(self, data):
        self._sweep_pending_delivery()
        try:
            env = proto.decode(data)
        except Exception as e:
            self._log("decode failed: " + str(e), RNS.LOG_DEBUG)
            return
        if not isinstance(env, dict):
            return
        t = env.get(proto.K_T)
        if t is None:
            return

        handler = self._PACKET_HANDLERS.get(t)
        if handler is not None:
            try:
                handler(self, env)
            except Exception as e:
                self._log("packet handler failed: " + str(e), RNS.LOG_DEBUG)

    def _handle_ping(self, env):
        with contextlib.suppress(Exception):
            pong = proto.make_envelope(
                proto.T_PONG,
                src=self.manager.identity.hash,
                body=env.get(proto.K_BODY),
            )
            self._send_env(pong)

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
            limits = body.get(proto.B_WELCOME_LIMITS)
            if isinstance(limits, dict):
                self._apply_limits(limits)
        with self._lock:
            was_reconnect = self._had_session
            self._reconnect_attempts = 0
            self._had_session = True
            rooms = list(self.rooms)
        self._set_status(RRCHub.STATUS_CONNECTED, "Connected")
        if was_reconnect and rooms:
            self._record_connection_event("Reconnected to hub", rooms=rooms)
        self.manager._on_welcome(self)
        if self.auto_list:
            self._request_room_list()

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

            # A hub that reports a join for a room we never entered must not
            # create phantom membership/state here.
            member = self_join or r in self.rooms
            if member:
                self.rooms.add(r)
                if r not in self.messages:
                    self.messages[r] = []
                members = self.members.setdefault(r, set())
                for h in body_hashes:
                    members.add(h)
                if own_hash is not None:
                    members.add(own_hash)

            if (
                member
                and (not self_join)
                and isinstance(joiner_nick, str)
                and joiner_nick
                and len(body_hashes) == 1
            ):
                jh = body_hashes[0]
                if own_hash is None or jh != own_hash:
                    self.nicks[jh] = joiner_nick

        if self_join:
            if silent:
                self._record_system(r, "You rejoined #" + r)
            else:
                self._record_system(r, "You joined #" + r)
            if self.auto_who:
                try:
                    with self._lock:
                        self._silent_who_rooms.add(r)
                    self._silent_who_ts[r] = time.monotonic()
                    self.send_command("/who " + r, room=r, record_local=False)
                except Exception:
                    with self._lock:
                        self._silent_who_rooms.discard(r)
                        self._silent_who_ts.pop(r, None)
            # Resend once messages that failed when the previous link dropped.
            # The JOINED confirm is in, so the retry lands in a real room.
            for m in list(self.messages.get(r, [])):
                if m.delivery == "failed" and not getattr(m, "_auto_retried", False):
                    m._auto_retried = True
                    with contextlib.suppress(Exception):
                        self.retry_message(r, m.seq)
            self.manager.save()
        else:
            joiner = None
            if len(body_hashes) == 1 and (
                own_hash is None or body_hashes[0] != own_hash
            ):
                joiner = body_hashes[0]
            if joiner is not None:
                self._record_system(
                    r, self.display_name_for(joiner) + " joined", event="join"
                )
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
                self._record_system(
                    r, self.display_name_for(parter) + " left", event="part"
                )
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
        own_echo = False
        if is_own and isinstance(mid, (bytes, bytearray)):
            with self._lock:
                own_echo = bytes(mid) in self._sent_ids
        if own_echo:
            self._confirm_delivery(bytes(mid))
            return
        if isinstance(src, (bytes, bytearray)) and isinstance(nick, str) and nick:
            with self._lock:
                self.nicks[bytes(src)] = nick
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

        # Only the hub may drive protocol state via NOTICE. Peer NOTICEs are
        # fanned out to room members with src rewritten to the peer's hash, so
        # without this check any member could spoof nick overrides, room
        # lists, WHO results, or the MOTD. A missing src is unattributed and
        # can only come from the hub itself.
        is_hub_src = src is None or (
            self._hub_identity_hash is not None
            and isinstance(src, (bytes, bytearray))
            and bytes(src) == bytes(self._hub_identity_hash)
        )

        nick_prefix = "nickname set to "
        if body.startswith(nick_prefix) and is_hub_src:
            new_nick = body[len(nick_prefix) :].strip()
            if new_nick:
                self.set_nick_override(new_nick)

        parsed = proto.parse_room_list_notice_details(body)
        if parsed is not None and is_hub_src:
            with self._lock:
                self.available_rooms = {
                    name: info.get("topic") for name, info in parsed.items()
                }
                self.available_keyed_rooms = sorted(
                    name for name, info in parsed.items() if info.get("has_key")
                )
                now = time.monotonic()
                if now > self._silent_list_deadline:
                    self._silent_list_pending = 0
                silent = self._silent_list_pending > 0
                if silent:
                    self._silent_list_pending -= 1
            self.manager._notify_change(self)
            if silent:
                return

        parsed_who = proto.parse_who_notice(body)
        if parsed_who is not None and is_hub_src:
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
                # A stale silent marker must not swallow a manual /who reply.
                stale = [
                    k
                    for k, ts in self._silent_who_ts.items()
                    if time.monotonic() - ts > 60.0
                ]
                for k in stale:
                    self._silent_who_rooms.discard(k)
                    self._silent_who_ts.pop(k, None)
                silent_who = who_room in self._silent_who_rooms
                if silent_who:
                    self._silent_who_rooms.discard(who_room)
                    self._silent_who_ts.pop(who_room, None)
            self.manager._notify_change(self)
            if silent_who:
                return

        room_n = room.strip().lower() if isinstance(room, str) else None
        if room_n is None and isinstance(body, str) and body.strip() and is_hub_src:
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
        leave_rooms = []
        with self._lock:
            if r:
                if r in self._pending_joins and self.manager.is_fatal_join_error(
                    text,
                ):
                    rollback_join = True
                self._pending_joins.discard(r)
                self._silent_joins.discard(r)
                self._pending_parts.discard(r)
                if rollback_join:
                    self.rooms.discard(r)
                    self.unread_rooms.discard(r)
                    self.mention_rooms.discard(r)
                    self.unread_counts.pop(r, None)
                    leave_rooms.append(r)
                elif self.manager.is_forced_leave_error(text) and r in self.rooms:
                    self.rooms.discard(r)
                    self.members.pop(r, None)
                    self.unread_rooms.discard(r)
                    self.mention_rooms.discard(r)
                    self.unread_counts.pop(r, None)
                    leave_rooms.append(r)
            elif self.manager.is_forced_leave_error(text):
                # A bare forced-leave error names no room; keep the persisted
                # history so one packet cannot wipe the whole archive.
                leave_rooms = list(self.rooms)
                self._pending_joins.clear()
                self._silent_joins.clear()
                self._pending_parts.clear()
                for room_name in leave_rooms:
                    self.rooms.discard(room_name)
                    self.members.pop(room_name, None)
                    self.unread_rooms.discard(room_name)
                    self.mention_rooms.discard(room_name)
                    self.unread_counts.pop(room_name, None)
        if r and self.manager.is_bad_key_error(text):
            with contextlib.suppress(Exception):
                self.manager.forget_room_key(self, r)
        msg = proto.RRCMessage("error", r, None, None, text, proto.now_ms())
        self._record_notice(msg)
        if rollback_join or leave_rooms:
            # History files survive forced-leave and fatal-join errors:
            # only remove_room/clear_messages delete the archive. A hub
            # error string must never decide what data gets erased.
            with self._lock:
                for room_name in leave_rooms:
                    self.messages.pop(room_name, None)
                    self.members.pop(room_name, None)
            for room_name in leave_rooms:
                if self.manager.active_room_for(self) == room_name:
                    self.manager.set_active(self, None)
            self.manager.save()
            self.manager._notify_change(self)

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
                # Expiry is otherwise only evaluated when a resource concludes,
                # so a hub that never sends resources must not grow this dict.
                now = time.monotonic()
                expired = [
                    k
                    for k, v in self._resource_expectations.items()
                    if v.get("expires", 0) < now
                ]
                for k in expired:
                    self._resource_expectations.pop(k, None)
                if len(self._resource_expectations) >= 256:
                    return
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

    _PACKET_HANDLERS: ClassVar = {
        proto.T_PING: _handle_ping,
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
                    msg = proto.RRCMessage(
                        "notice", room, None, None, text, proto.now_ms()
                    )
                    self._record_notice(msg)
                else:
                    # An oversized notice (eg a big /list) still carries the
                    # same command responses. Run it through the normal notice
                    # path so room lists and /who results actually populate.
                    self._handle_notice(
                        {
                            proto.K_T: proto.T_NOTICE,
                            proto.K_BODY: text,
                            proto.K_ROOM: room,
                            proto.K_SRC: None,
                        }
                    )
        except Exception as e:
            self._log("resource handling failed: " + str(e), RNS.LOG_ERROR)

    def _current_rtt_ms(self):
        """Best available link RTT in ms, from link setup timing."""
        link = self.link
        if link is None or isinstance(link, _LoopbackEndpoint):
            return None
        rtt = getattr(link, "rtt", None)
        if isinstance(rtt, (int, float)) and rtt > 0:
            return int(rtt * 1000)
        return None

    def to_dict(self):
        """Return a JSON-serializable summary of this hub's state."""
        stored_key_rooms = []
        with contextlib.suppress(Exception):
            stored_key_rooms = [
                entry["room"] for entry in self.manager.list_stored_room_keys(self)
            ]
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
                "available_keyed_rooms": list(self.available_keyed_rooms),
                "stored_key_rooms": stored_key_rooms,
                "auto_reconnect": bool(self.auto_reconnect),
                "rtt_ms": self._current_rtt_ms(),
                "auto_list": bool(self.auto_list),
                "auto_who": bool(self.auto_who),
                "nick_override": self.nick_override,
                "max_msg_body_bytes": self.max_msg_body_bytes,
            }

    def room_messages(self, room, limit=None, before_seq=None):
        self._sweep_pending_delivery()
        """Return (messages, has_more) for a room, newest page last.

        before_seq, when given, restricts results to messages recorded
        before that sequence number, letting callers page backwards through
        history. limit caps how many of the most recent matching messages
        are returned. Has_more reports whether older messages remain.
        """
        msgs = self.get_messages(proto.normalize_room(room))
        if before_seq is not None:
            seqs = [m.seq or 0 for m in msgs]
            cut = bisect.bisect_left(seqs, before_seq)
            msgs = msgs[:cut]
        has_more = False
        if limit is not None and len(msgs) > limit:
            has_more = True
            msgs = msgs[-limit:]
        return [m.to_dict() for m in msgs], has_more

    def members_dict(self, room):
        """Return serialized members for a room."""
        r = proto.normalize_room(room)
        out = [
            {"hash": h.hex(), "name": self.display_name_for(h)}
            for h in self.get_members(r)
        ]
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
        history_per_room_cap=500,
        filter_loaded_history=True,
        ephemeral_notices=RRCHub.SYS_NOTICE_TIMEOUT,
        database=None,
    ):
        self.identity = identity
        self.storage_dir = storage_dir
        self._get_nickname = get_nickname
        self.get_name_for_identity_hash = get_name_for_identity_hash
        self.history_per_room_cap = history_per_room_cap
        self.filter_loaded_history = filter_loaded_history
        self.ephemeral_notices = ephemeral_notices
        self.database = database

        self.hubs = []
        self._server_manager = None
        self._lock = threading.RLock()
        self._change_callback = None
        self._message_callback = None
        self._active_hub = None
        self._active_room = None
        self._loaded = False
        self._loading = False
        self._interface_wait_done = False
        self._save_lock = threading.Lock()

    def set_database(self, database):
        self.database = database

    def _private_key_bytes(self):
        identity = self.identity
        if identity is None:
            return None
        with contextlib.suppress(Exception):
            key = identity.get_private_key()
            if isinstance(key, (bytes, bytearray)) and key:
                return bytes(key)
        return None

    def _room_key_dao(self):
        db = self.database
        if db is None:
            return None
        return getattr(db, "rrc_room_keys", None)

    @staticmethod
    def _hub_hash_hex(hub_or_hash):
        if isinstance(hub_or_hash, RRCHub):
            return hub_or_hash.hub_hash.hex()
        if isinstance(hub_or_hash, (bytes, bytearray)):
            return bytes(hub_or_hash).hex()
        if isinstance(hub_or_hash, str):
            return hub_or_hash.strip().lower()
        msg = "invalid hub hash"
        raise TypeError(msg)

    @staticmethod
    def _dest_name_for(hub_or_dest):
        if isinstance(hub_or_dest, RRCHub):
            return hub_or_dest.dest_name or DEFAULT_DEST_NAME
        if isinstance(hub_or_dest, str) and hub_or_dest.strip():
            return hub_or_dest.strip()
        return DEFAULT_DEST_NAME

    def remember_room_key(self, hub, room, key):
        """Encrypt and persist a room key for later joins."""
        dao = self._room_key_dao()
        private_key = self._private_key_bytes()
        if dao is None or private_key is None:
            msg = "room key storage is unavailable"
            raise RuntimeError(msg)
        room_n = proto.normalize_room(room)
        nonce, ciphertext = encrypt_room_key(private_key, key)
        dao.upsert(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
            nonce,
            ciphertext,
        )

    def forget_room_key(self, hub, room):
        dao = self._room_key_dao()
        if dao is None:
            return 0
        room_n = proto.normalize_room(room)
        return dao.delete(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
        )

    def get_room_key(self, hub, room):
        """Return the decrypted room key, or None when missing or undecryptable."""
        dao = self._room_key_dao()
        private_key = self._private_key_bytes()
        if dao is None or private_key is None:
            return None
        room_n = proto.normalize_room(room)
        row = dao.get(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
        )
        if not row:
            return None
        try:
            return decrypt_room_key(private_key, row["nonce"], row["ciphertext"])
        except Exception:
            return None

    def has_stored_room_key(self, hub, room):
        dao = self._room_key_dao()
        if dao is None:
            return False
        room_n = proto.normalize_room(room)
        row = dao.get(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
        )
        return row is not None

    def list_stored_room_keys(self, hub):
        dao = self._room_key_dao()
        if dao is None:
            return []
        rows = dao.list_for_hub(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
        )
        return [
            {
                "hub_hash": row["hub_hash"],
                "dest_name": row["dest_name"],
                "room": row["room"],
                "updated_at": row.get("updated_at"),
            }
            for row in rows or []
        ]

    @staticmethod
    def is_bad_key_error(text):
        if not isinstance(text, str):
            return False
        lowered = text.strip().lower()
        # Require the words "bad key" so mode hints like "enable +k" do not wipe storage.
        return any(marker in lowered for marker in BAD_KEY_MARKERS)

    @staticmethod
    def is_forced_leave_error(text):
        if not isinstance(text, str):
            return False
        lowered = text.strip().lower()
        return any(marker in lowered for marker in FORCED_LEAVE_MARKERS)

    @staticmethod
    def is_fatal_join_error(text):
        """Whether a JOIN error means the room can never be joined.

        Transient failures like rate limiting must keep room membership
        and history so saved rooms can retry on the next connect.
        """
        if not isinstance(text, str):
            return False
        lowered = text.strip().lower()
        return any(marker in lowered for marker in JOIN_FATAL_MARKERS)

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
        """Return a running locally hosted hub matching hub_hash, if any."""
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
        with hub._lock:
            rooms_to_rejoin = list(hub.rooms)
        for r in rooms_to_rejoin:
            with contextlib.suppress(Exception):
                key = self.get_room_key(hub, r)
                hub.join_room(r, key=key, silent=True)

    def set_active(self, hub, room):
        with contextlib.suppress(ValueError):
            room = proto.normalize_room(room)
        self._active_hub = hub
        self._active_room = room
        if hub is not None and room is not None:
            hub.mark_read(room)

    def active_room_for(self, hub):
        if self._active_hub is hub:
            return self._active_room
        return None

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
        dao = self._room_key_dao()
        if dao is not None:
            with contextlib.suppress(Exception):
                dao.delete_for_hub(
                    self._hub_hash_hex(hub),
                    self._dest_name_for(hub),
                )
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

    def _wait_for_first_interface(self, timeout_s=15.0):
        """Block until some interface is online so path requests reach the mesh.

        Startup fires connect attempts as soon as Reticulum exists, but TCP
        client interfaces and shared-instance links take a beat to come up.
        A path request sent in that gap is dropped and costs a whole response
        window before the hub fails over to reconnect backoff. Wait briefly
        for any online interface instead. Interfaces absent entirely (pure
        loopback setups) bail after a short grace so nothing stalls forever.
        """
        deadline = time.monotonic() + timeout_s
        empty_grace = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            try:
                reticulum = RNS.Reticulum.get_instance()
            except Exception:
                # No Reticulum at all (degraded mode): nothing to wait for.
                return False
            try:
                stats = reticulum.get_interface_stats()
                interfaces = stats.get("interfaces", [])
                if not isinstance(interfaces, (list, tuple)):
                    interfaces = []
                for iface in interfaces:
                    if iface.get("status"):
                        return True
                if not interfaces and time.monotonic() > empty_grace:
                    return False
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def connect_auto_reconnect_hubs(self):
        """Connect hubs that have auto-reconnect enabled (e.g. after startup load)."""
        with self._lock:
            hubs = [h for h in self.hubs if h.auto_reconnect]
        if not hubs:
            return
        if not self._interface_wait_done:
            self._interface_wait_done = True
            self._wait_for_first_interface()
        started = 0
        for hub in hubs:
            with hub._lock:
                if hub.status in (
                    RRCHub.STATUS_CONNECTING,
                    RRCHub.STATUS_CONNECTED,
                ):
                    continue
            hub.connect()
            started += 1
            if started < len(hubs):
                time.sleep(AUTO_CONNECT_STAGGER_S)

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
                with self._lock:
                    entries = [self._hub_entry(h) for h in self.hubs]
                data = proto.encode({"hubs": entries})
                atomic_write_bytes(path, data)
            except Exception:
                with contextlib.suppress(Exception):
                    os.unlink(tmp_path)

    def _hub_entry(self, h):
        with h._lock:
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
