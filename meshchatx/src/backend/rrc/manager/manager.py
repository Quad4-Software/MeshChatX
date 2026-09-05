# SPDX-License-Identifier: 0BSD

"""RRC manager owning the collection of configured hubs."""

import contextlib
import threading

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager.hub import RRCHub
from meshchatx.src.backend.rrc.manager.persistence import RRCManagerPersistenceMixin
from meshchatx.src.backend.rrc.manager.room_keys import RRCManagerRoomKeysMixin


class RRCManager(RRCManagerRoomKeysMixin, RRCManagerPersistenceMixin):
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
        self._save_lock = threading.Lock()

    def set_database(self, database):
        self.database = database

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
        for r in list(hub.rooms):
            with contextlib.suppress(Exception):
                key = self.get_room_key(hub, r)
                hub.join_room(r, key=key, silent=True)

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
