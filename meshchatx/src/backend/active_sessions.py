# SPDX-License-Identifier: 0BSD

"""Track active UI WebSocket sessions (IP and user-agent) for local multi-client warnings."""

from __future__ import annotations

import ipaddress
import threading
import time
import uuid
from typing import Any

_MAX_UA_LEN = 512
_MAX_IP_LEN = 128


def _clean_ip(value: str | None) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return "unknown"
    return cleaned[:_MAX_IP_LEN]


def _clean_user_agent(value: str | None) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return "unknown"
    # Strip control characters that break logs or JSON displays.
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    if not cleaned:
        return "unknown"
    return cleaned[:_MAX_UA_LEN]


def is_loopback_or_lan_ip(value: str | None) -> bool:
    """True for loopback, RFC1918, link-local, and IPv6 ULA addresses."""
    cleaned = str(value or "").strip()
    if not cleaned or cleaned.lower() == "unknown":
        return False
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    if "%" in cleaned:
        cleaned = cleaned.split("%", 1)[0]
    if cleaned.lower().startswith("::ffff:"):
        cleaned = cleaned[7:]
    try:
        addr = ipaddress.ip_address(cleaned)
    except ValueError:
        return False
    return bool(addr.is_loopback or addr.is_private or addr.is_link_local)


def sessions_are_local_only(sessions: Any) -> bool:
    """True when every session IP is loopback or LAN (or the list is empty)."""
    if sessions is None:
        return False
    try:
        rows = list(sessions)
    except TypeError:
        return False
    if not rows:
        return True
    for row in rows:
        if not isinstance(row, dict):
            return False
        if not is_loopback_or_lan_ip(row.get("ip")):
            return False
    return True


def should_warn_multi_session(
    count: int,
    warning_enabled: bool,
    sessions: Any = None,
) -> bool:
    """Oracle: warn when two or more non-local sessions are active and the setting is on.

    Localhost and LAN-only clients (same machine or private network) do not
    trigger the toast. Pass sessions=None to skip the locality check.
    """
    try:
        active = int(count)
    except (TypeError, ValueError):
        return False
    if not bool(warning_enabled) or active < 2:
        return False
    if sessions is not None and sessions_are_local_only(sessions):
        return False
    return True


class ActiveSessionTracker:
    """In-memory registry of connected MeshChatX UI WebSocket clients."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, dict[str, Any]] = {}

    def add(self, *, ip: str | None, user_agent: str | None) -> dict[str, Any]:
        session_id = uuid.uuid4().hex
        entry = {
            "id": session_id,
            "ip": _clean_ip(ip),
            "user_agent": _clean_user_agent(user_agent),
            "connected_at": time.time(),
        }
        with self._lock:
            self._sessions[session_id] = entry
            return dict(entry)

    def remove(self, session_id: str | None) -> bool:
        cleaned = str(session_id or "").strip()
        if not cleaned:
            return False
        with self._lock:
            return self._sessions.pop(cleaned, None) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(row) for row in self._sessions.values()]
        rows.sort(key=lambda row: float(row.get("connected_at") or 0.0))
        return rows

    def snapshot(self) -> dict[str, Any]:
        sessions = self.list_sessions()
        return {
            "count": len(sessions),
            "sessions": sessions,
        }
