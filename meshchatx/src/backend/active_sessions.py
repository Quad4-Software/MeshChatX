# SPDX-License-Identifier: 0BSD

"""Track active UI WebSocket sessions (IP and user-agent) for local multi-client warnings."""

from __future__ import annotations

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


def should_warn_multi_session(count: int, warning_enabled: bool) -> bool:
    """Oracle: warn when two or more sessions are active and the setting is on."""
    try:
        active = int(count)
    except (TypeError, ValueError):
        return False
    return bool(warning_enabled) and active >= 2


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
