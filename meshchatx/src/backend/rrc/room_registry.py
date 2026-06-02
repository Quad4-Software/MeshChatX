# SPDX-License-Identifier: 0BSD

"""Room state, modes, and rooms.toml persistence for hosted RRC hubs."""

import time

from meshchatx.src.backend.rrc.rooms_toml import INVITE_DEFAULT_TTL_S


def default_room_state(*, founder=None, registered=False, topic=None, private=False):
    return {
        "founder": founder,
        "registered": bool(registered),
        "topic": topic,
        "moderated": False,
        "invite_only": False,
        "topic_ops_only": False,
        "no_outside_msgs": False,
        "private": bool(private),
        "key": None,
        "ops": set([founder]) if founder is not None else set(),
        "voiced": set(),
        "bans": set(),
        "invited": {},
        "last_used_ts": None,
    }


class RoomRegistry:
    """Tracks per-room modes, ACLs, and registered room metadata."""

    def __init__(self, hub, toml_store):
        self.hub = hub
        self._store = toml_store
        self._registry = {}
        self._state = {}
        if toml_store is not None:
            self._registry = toml_store.load()
            for name, reg in self._registry.items():
                self._state[name] = dict(reg)

    def reload(self):
        if self._store is None:
            return
        self._registry = self._store.load()
        for name, reg in self._registry.items():
            self._state[name] = dict(reg)

    def get_state(self, room):
        return self._state.get(room)

    def ensure_state(self, room, *, founder=None):
        st = self._state.get(room)
        if st is not None:
            if st.get("founder") is None and founder is not None:
                st["founder"] = founder
                st.setdefault("ops", set()).add(founder)
            return st
        if room in self._registry:
            base = dict(self._registry[room])
            invited = base.get("invited")
            if isinstance(invited, dict):
                base["invited"] = dict(invited)
            for key in ("ops", "voiced", "bans"):
                val = base.get(key)
                if isinstance(val, set):
                    base[key] = set(val)
                elif isinstance(val, list):
                    base[key] = set(val)
                else:
                    base[key] = set()
            self._state[room] = base
            return base
        st = default_room_state(founder=founder, registered=False)
        self._state[room] = st
        return st

    def touch_room(self, room):
        st = self.ensure_state(room)
        st["last_used_ts"] = float(time.time())

    def register_room(self, room, **kwargs):
        st = self.ensure_state(room, founder=kwargs.get("founder"))
        st["registered"] = True
        if "topic" in kwargs:
            st["topic"] = kwargs["topic"]
        if "private" in kwargs:
            st["private"] = bool(kwargs["private"])
        for flag in (
            "moderated",
            "invite_only",
            "topic_ops_only",
            "no_outside_msgs",
        ):
            if flag in kwargs:
                st[flag] = bool(kwargs[flag])
        if "key" in kwargs:
            key = kwargs["key"]
            st["key"] = key if isinstance(key, str) and key else None
        if "founder" in kwargs and kwargs["founder"] is not None:
            st["founder"] = kwargs["founder"]
            st.setdefault("ops", set()).add(kwargs["founder"])
        self._registry[room] = dict(st)
        self.persist(room)

    def unregister_room(self, room):
        st = self._state.get(room)
        if st is not None:
            st["registered"] = False
        self._registry.pop(room, None)
        self.persist(room)

    def persist(self, room):
        if self._store is None:
            return
        st = self._state.get(room)
        if not st or not st.get("registered"):
            merged = dict(self._registry)
            if room in merged and not merged[room].get("registered"):
                merged.pop(room, None)
            self._store.save(merged)
            return
        self._registry[room] = {
            "founder": st.get("founder"),
            "registered": True,
            "topic": st.get("topic"),
            "moderated": bool(st.get("moderated")),
            "invite_only": bool(st.get("invite_only")),
            "topic_ops_only": bool(st.get("topic_ops_only")),
            "no_outside_msgs": bool(st.get("no_outside_msgs")),
            "private": bool(st.get("private")),
            "key": st.get("key"),
            "ops": set(st.get("ops") or set()),
            "voiced": set(st.get("voiced") or set()),
            "bans": set(st.get("bans") or set()),
            "invited": dict(st.get("invited") or {}),
            "last_used_ts": st.get("last_used_ts"),
        }
        self._store.save(self._registry)

    def delete_from_registry(self, room):
        self._registry.pop(room, None)
        self._state.pop(room, None)
        if self._store is not None:
            self._store.save(self._registry)

    def get_mode_string(self, room):
        st = self.ensure_state(room)
        flags = []
        if st.get("invite_only"):
            flags.append("i")
        if isinstance(st.get("key"), str) and st.get("key"):
            flags.append("k")
        if st.get("moderated"):
            flags.append("m")
        if st.get("no_outside_msgs"):
            flags.append("n")
        if st.get("private"):
            flags.append("p")
        if st.get("topic_ops_only"):
            flags.append("t")
        if st.get("registered"):
            flags.append("r")
        return "+" + "".join(flags) if flags else "(none)"

    def broadcast_mode(self, room, outgoing):
        mode_txt = self.get_mode_string(room)
        text = f"mode for {room} is now: {mode_txt}"
        for link in list(self.hub._room_members.get(room, set())):
            self.hub._queue_notice(outgoing, link, room, text)

    def is_room_op(self, room, peer_hash):
        if peer_hash is None:
            return False
        if self.hub.policy.is_server_op(peer_hash):
            return True
        st = self.ensure_state(room)
        founder = st.get("founder")
        if isinstance(founder, (bytes, bytearray)) and bytes(founder) == bytes(
            peer_hash
        ):
            return True
        ops = st.get("ops")
        return isinstance(ops, set) and bytes(peer_hash) in ops

    def is_room_voiced(self, room, peer_hash):
        if peer_hash is None:
            return False
        if self.is_room_op(room, peer_hash):
            return True
        st = self.ensure_state(room)
        voiced = st.get("voiced")
        return isinstance(voiced, set) and bytes(peer_hash) in voiced

    def is_room_moderated(self, room):
        st = self.ensure_state(room)
        return bool(st.get("moderated"))

    def is_room_banned(self, room, peer_hash):
        if peer_hash is None:
            return False
        st = self.ensure_state(room)
        bans = st.get("bans")
        return isinstance(bans, set) and bytes(peer_hash) in bans

    def is_invited(self, room, peer_hash):
        st = self.ensure_state(room)
        inv = st.get("invited")
        if not isinstance(inv, dict) or not inv:
            return False
        now = float(time.time())
        exp = inv.get(bytes(peer_hash))
        try:
            exp_f = float(exp) if exp is not None else 0.0
        except (TypeError, ValueError):
            exp_f = 0.0
        if exp_f <= now:
            inv.pop(bytes(peer_hash), None)
            return False
        return True

    def prune_expired_invites(self, room):
        st = self.ensure_state(room)
        inv = st.get("invited")
        if not isinstance(inv, dict) or not inv:
            return False
        now = float(time.time())
        removed = False
        for h, exp in list(inv.items()):
            try:
                exp_f = float(exp)
            except (TypeError, ValueError):
                exp_f = 0.0
            if exp_f <= now:
                inv.pop(h, None)
                removed = True
        return removed

    def add_invite(self, room, peer_hash, ttl_s=None):
        st = self.ensure_state(room)
        inv = st.setdefault("invited", {})
        ttl = float(ttl_s) if ttl_s is not None else INVITE_DEFAULT_TTL_S
        if ttl <= 0:
            ttl = INVITE_DEFAULT_TTL_S
        inv[bytes(peer_hash)] = float(time.time()) + ttl

    def room_config_for_api(self, room):
        st = self.ensure_state(room)
        ops = st.get("ops") or set()
        voiced = st.get("voiced") or set()
        bans = st.get("bans") or set()
        invited = st.get("invited") or {}
        return {
            "name": room,
            "topic": st.get("topic"),
            "private": bool(st.get("private")),
            "registered": bool(st.get("registered")),
            "moderated": bool(st.get("moderated")),
            "invite_only": bool(st.get("invite_only")),
            "topic_ops_only": bool(st.get("topic_ops_only")),
            "no_outside_msgs": bool(st.get("no_outside_msgs")),
            "has_key": bool(isinstance(st.get("key"), str) and st.get("key")),
            "founder": bytes(st["founder"]).hex()
            if isinstance(st.get("founder"), (bytes, bytearray))
            else None,
            "operators": sorted(bytes(x).hex() for x in ops),
            "voiced": sorted(bytes(x).hex() for x in voiced),
            "bans": sorted(bytes(x).hex() for x in bans),
            "invite_count": len(invited),
            "modes": self.get_mode_string(room),
        }
