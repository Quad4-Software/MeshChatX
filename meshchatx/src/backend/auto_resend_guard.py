# SPDX-License-Identifier: 0BSD
"""Guards for auto-resending failed LXMF messages without flooding peers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

# Max automatic replacement sends per failed lineage before requiring manual retry.
MAX_AUTO_RESEND_ATTEMPTS = 3
# Minimum seconds between auto-resend claims for the same failed row.
AUTO_RESEND_COOLDOWN_SECONDS = 120
# Skip auto-resend when a recent outbound with the same body already exists.
RECENT_SAME_CONTENT_SECONDS = 300
# Idle per-destination locks retained after identity/destination churn.
MAX_AUTO_RESEND_LOCKS = 256

AUTO_RESEND_COUNT_FIELD = "_mcx_auto_resend_count"


def content_fingerprint(content: str | None) -> str:
    raw = (content or "").encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def read_auto_resend_count(fields_raw: Any) -> int:
    fields = _parse_fields(fields_raw)
    try:
        return max(0, int(fields.get(AUTO_RESEND_COUNT_FIELD, 0)))
    except (TypeError, ValueError):
        return 0


def fields_with_auto_resend_count(fields_raw: Any, count: int) -> str:
    fields = _parse_fields(fields_raw)
    fields[AUTO_RESEND_COUNT_FIELD] = max(0, int(count))
    return json.dumps(fields)


def _parse_fields(fields_raw: Any) -> dict:
    if isinstance(fields_raw, dict):
        return dict(fields_raw)
    if not fields_raw:
        return {}
    if isinstance(fields_raw, str):
        try:
            parsed = json.loads(fields_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class AutoResendCoordinator:
    """Per destination asyncio lock so announce/ping/path cannot race-resend."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def lock_for(self, identity_key: str, destination_hash: str) -> asyncio.Lock:
        key = f"{identity_key}:{destination_hash}"
        lock = self._locks.get(key)
        if lock is not None:
            self._locks.pop(key, None)
            self._locks[key] = lock
            return lock
        self.evict_unlocked_locks(keep=MAX_AUTO_RESEND_LOCKS - 1)
        lock = asyncio.Lock()
        self._locks[key] = lock
        return lock

    def evict_unlocked_locks(self, keep: int = MAX_AUTO_RESEND_LOCKS) -> int:
        """Drop oldest unlocked locks until at most keep remain."""
        cap = max(0, int(keep))
        dropped = 0
        if len(self._locks) <= cap:
            return 0
        for key in list(self._locks.keys()):
            if len(self._locks) <= cap:
                break
            lock = self._locks.get(key)
            if lock is None or lock.locked():
                continue
            del self._locks[key]
            dropped += 1
        return dropped

    def drop_identity(self, identity_key: str) -> int:
        prefix = f"{identity_key}:"
        dropped = 0
        for key in [k for k in self._locks if k.startswith(prefix)]:
            lock = self._locks.get(key)
            if lock is not None and lock.locked():
                continue
            self._locks.pop(key, None)
            dropped += 1
        return dropped


def fields_have_attachments(fields_raw: Any) -> bool:
    fields = _parse_fields(fields_raw)
    if not fields:
        return False
    if fields.get("image") or fields.get("audio"):
        return True
    files = fields.get("file_attachments")
    return isinstance(files, list) and len(files) > 0


def parse_fields_dict(fields_raw: Any) -> dict:
    return _parse_fields(fields_raw)


def should_skip_for_budget(
    fields_raw: Any,
    *,
    max_attempts: int = MAX_AUTO_RESEND_ATTEMPTS,
) -> bool:
    return read_auto_resend_count(fields_raw) >= max_attempts


def next_attempt_count(fields_raw: Any) -> int:
    return read_auto_resend_count(fields_raw) + 1


def cooldown_until(
    now: float | None = None,
    *,
    seconds: int = AUTO_RESEND_COOLDOWN_SECONDS,
) -> float:
    return float(now if now is not None else time.time()) + float(seconds)
