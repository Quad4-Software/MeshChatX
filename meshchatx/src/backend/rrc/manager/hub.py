# SPDX-License-Identifier: 0BSD

"""RRC hub connection representation and state tracking."""

import contextlib
import threading
from collections import deque

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager.actions import RRCHubActionsMixin
from meshchatx.src.backend.rrc.manager.connection import RRCHubConnectionMixin
from meshchatx.src.backend.rrc.manager.handlers import RRCHubPacketHandlersMixin
from meshchatx.src.backend.rrc.manager.history import RRCHubHistoryMixin


class RRCHub(
    RRCHubHistoryMixin,
    RRCHubConnectionMixin,
    RRCHubActionsMixin,
    RRCHubPacketHandlersMixin,
):
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
        self._had_session = False
        self._pending_pings = {}
        self._last_history_clean = 0
        self.clean_last_removed = 0

        self.available_rooms = {}
        self.available_keyed_rooms = []
        self._silent_list_pending = 0
        self._silent_who_rooms = set()

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

    def _own_hash(self):
        return self.manager.identity.hash if self.manager.identity is not None else None

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
                "auto_list": bool(self.auto_list),
                "auto_who": bool(self.auto_who),
                "nick_override": self.nick_override,
                "max_msg_body_bytes": self.max_msg_body_bytes,
            }

    def members_dict(self, room):
        """Return serialized members for a room."""
        r = proto.normalize_room(room)
        out = []
        for h in self.get_members(r):
            out.append({"hash": h.hex(), "name": self.display_name_for(h)})
        out.sort(key=lambda m: m["name"].lower())
        return out
