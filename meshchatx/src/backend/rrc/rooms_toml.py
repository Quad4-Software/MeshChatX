# SPDX-License-Identifier: 0BSD

"""Load and save rrcd-compatible rooms.toml for hosted RRC hubs."""

import os
import threading
import time
import tomllib

from meshchatx.src.backend.rrc.identity_util import parse_identity_hash

INVITE_DEFAULT_TTL_S = 900.0


def _parse_hash_list(items):
    out = set()
    if not isinstance(items, list):
        return out
    for item in items:
        h = parse_identity_hash(str(item)) if item is not None else None
        if h is not None:
            out.add(h)
    return out


def _parse_invited_table(raw, now=None):
    invited = {}
    if not isinstance(raw, dict):
        return invited
    now = float(time.time()) if now is None else now
    for key, exp in raw.items():
        h = parse_identity_hash(str(key))
        if h is None:
            continue
        try:
            exp_f = float(exp)
        except (TypeError, ValueError):
            continue
        if exp_f > now:
            invited[h] = exp_f
    return invited


def load_rooms_registry(path):
    """Load room registry from rooms.toml. Returns dict room_name -> state dict."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "rb") as f:
            doc = tomllib.load(f)
    except Exception:
        return {}
    rooms_section = doc.get("rooms")
    if not isinstance(rooms_section, dict):
        return {}
    registry = {}
    now = float(time.time())
    for room_name, room_data in rooms_section.items():
        if not isinstance(room_data, dict):
            continue
        founder = room_data.get("founder")
        founder_b = None
        if isinstance(founder, str):
            founder_b = parse_identity_hash(founder)
        topic = room_data.get("topic")
        if not isinstance(topic, str):
            topic = None
        registry[str(room_name).strip().lower()] = {
            "founder": founder_b,
            "registered": True,
            "topic": topic,
            "moderated": bool(room_data.get("moderated", False)),
            "invite_only": bool(room_data.get("invite_only", False)),
            "topic_ops_only": bool(room_data.get("topic_ops_only", False)),
            "no_outside_msgs": bool(room_data.get("no_outside_msgs", False)),
            "private": bool(room_data.get("private", False)),
            "key": room_data.get("key")
            if isinstance(room_data.get("key"), str)
            else None,
            "ops": _parse_hash_list(room_data.get("operators", [])),
            "voiced": _parse_hash_list(room_data.get("voiced", [])),
            "bans": _parse_hash_list(room_data.get("bans", [])),
            "invited": _parse_invited_table(room_data.get("invited"), now=now),
            "last_used_ts": room_data.get("last_used_ts"),
        }
    return registry


def _toml_escape_string(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _dump_hash_list(values):
    if not values:
        return "[]"
    items = sorted(bytes(v).hex() for v in values if isinstance(v, (bytes, bytearray)))
    inner = ", ".join(_toml_escape_string(x) for x in items)
    return "[" + inner + "]"


def _dump_invited_table(invited):
    if not invited:
        return "{}"
    now = float(time.time())
    lines = []
    for h, exp in sorted(invited.items(), key=lambda x: bytes(x[0]).hex()):
        if not isinstance(h, (bytes, bytearray)):
            continue
        try:
            exp_f = float(exp)
        except (TypeError, ValueError):
            continue
        if exp_f <= now:
            continue
        lines.append(f"  {bytes(h).hex()} = {exp_f}")
    if not lines:
        return "{}"
    return "{\n" + "\n".join(lines) + "\n}"


def dump_rooms_registry(path, registry):
    """Write rooms.toml from registry dict (room -> state)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    lines = []
    for room in sorted(registry.keys()):
        st = registry[room]
        if not st.get("registered"):
            continue
        lines.append(f"[rooms.{room}]")
        founder = st.get("founder")
        if isinstance(founder, (bytes, bytearray)):
            lines.append(f"founder = {_toml_escape_string(bytes(founder).hex())}")
        topic = st.get("topic")
        if isinstance(topic, str) and topic.strip():
            lines.append(f"topic = {_toml_escape_string(topic)}")
        lines.append(f"moderated = {'true' if st.get('moderated') else 'false'}")
        lines.append(f"invite_only = {'true' if st.get('invite_only') else 'false'}")
        lines.append(
            f"topic_ops_only = {'true' if st.get('topic_ops_only') else 'false'}"
        )
        lines.append(
            f"no_outside_msgs = {'true' if st.get('no_outside_msgs') else 'false'}"
        )
        lines.append(f"private = {'true' if st.get('private') else 'false'}")
        key = st.get("key")
        if isinstance(key, str) and key:
            lines.append(f"key = {_toml_escape_string(key)}")
        ops = st.get("ops")
        if isinstance(ops, set) and ops:
            lines.append(f"operators = {_dump_hash_list(ops)}")
        voiced = st.get("voiced")
        if isinstance(voiced, set) and voiced:
            lines.append(f"voiced = {_dump_hash_list(voiced)}")
        bans = st.get("bans")
        if isinstance(bans, set) and bans:
            lines.append(f"bans = {_dump_hash_list(bans)}")
        invited = st.get("invited")
        if isinstance(invited, dict) and invited:
            inv_body = _dump_invited_table(invited)
            if inv_body != "{}":
                lines.append(f"invited = {inv_body}")
        last_used = st.get("last_used_ts")
        try:
            lines.append(f"last_used_ts = {float(last_used)}")
        except (TypeError, ValueError):
            lines.append(f"last_used_ts = {time.time()}")
        lines.append("")
    text = "\n".join(lines)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class RoomsTomlStore:
    """Thread-safe rooms.toml persistence for one hub."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            return load_rooms_registry(self.path)

    def save(self, registry):
        with self._lock:
            dump_rooms_registry(self.path, registry)
