# SPDX-License-Identifier: 0BSD

"""Hub configuration and history directory persistence mixin for RRCManager."""

import contextlib
import hashlib
import os

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager.constants import (
    HISTORY_DIR_NAME,
    HISTORY_FILENAME_SANITIZE_RE,
)


class RRCManagerPersistenceMixin:
    """Load, save, and history directory management for RRCManager."""

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
