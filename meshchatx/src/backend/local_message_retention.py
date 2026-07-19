# SPDX-License-Identifier: 0BSD
"""Local-only age-based deletion of stored LXMF rows (this device, no network signal)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime

log = logging.getLogger(__name__)

UNIT_DAYS = "days"
UNIT_MONTHS = "months"

SECONDS_PER_DAY = 86400
SECONDS_PER_MONTH = 30 * SECONDS_PER_DAY

RETENTION_CHECK_INTERVAL_SECONDS = 3600
LOCAL_RETENTION_STARTUP_GRACE_SECONDS = 120

MAX_VALUE_DAYS = 10_000
MAX_VALUE_MONTHS = 120


def normalize_unit(raw: str | None) -> str:
    s = (raw or UNIT_DAYS).strip().lower()
    if s in ("month", "months", "mo", "m"):
        return UNIT_MONTHS
    return UNIT_DAYS


def retention_window_seconds(value: int, unit: str) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = 1
    u = normalize_unit(unit)
    if u == UNIT_MONTHS:
        return max(1, min(v, MAX_VALUE_MONTHS)) * SECONDS_PER_MONTH
    return max(1, min(v, MAX_VALUE_DAYS)) * SECONDS_PER_DAY


def local_message_retention_cutoff_ts(now: float, value: int, unit: str) -> float:
    return float(now) - float(retention_window_seconds(value, unit))


def parse_before_cutoff(raw: str | None) -> float | None:
    """Parse a before cutoff from unix seconds or an ISO date/datetime string.

    YYYY-MM-DD is treated as midnight UTC on that calendar day (messages with
    timestamp strictly before that instant).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        pass
    try:
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            d = date.fromisoformat(s)
            return datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp()
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError as exc:
        raise ValueError("invalid before value") from exc


def resolve_message_age_cutoff(
    *,
    older_than_days: str | int | None = None,
    before: str | None = None,
    now: float | None = None,
) -> float | None:
    """Resolve a purge/export cutoff from query-style inputs.

    Returns None when neither filter is provided. Prefer ``before`` when both
    are set. Raises ValueError on invalid input.
    """
    before_raw = None if before is None else str(before).strip()
    if before_raw:
        cutoff = parse_before_cutoff(before_raw)
        if cutoff is None:
            raise ValueError("invalid before value")
        return float(cutoff)

    if older_than_days is None or str(older_than_days).strip() == "":
        return None
    try:
        days = int(older_than_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("older_than_days must be an integer") from exc
    if days < 1 or days > MAX_VALUE_DAYS:
        raise ValueError(f"older_than_days must be between 1 and {MAX_VALUE_DAYS}")
    return local_message_retention_cutoff_ts(
        now if now is not None else time.time(),
        days,
        UNIT_DAYS,
    )


def purge_messages_before_cutoff(
    messages,
    cancel_outbound: Callable[[bytes], None] | None,
    cutoff: float,
) -> int:
    """Delete local LXMF rows with timestamp strictly before cutoff.

    Attachments live in message row fields, so deleting the row removes them.
    Does not contact peers.
    """
    hashes = messages.list_message_hashes_with_timestamp_before(float(cutoff))
    if not hashes:
        return 0
    if cancel_outbound is not None:
        for h in hashes:
            if not h or len(h) % 2 != 0:
                continue
            try:
                cancel_outbound(bytes.fromhex(h))
            except Exception as exc:  # noqa: BLE001
                log.debug("purge_messages_before_cutoff cancel_outbound: %s", exc)
    messages.delete_lxmf_messages_by_hashes(hashes)
    messages.prune_conversation_metadata_for_peers_with_no_messages()
    return len(hashes)


def apply_local_message_retention(
    messages,
    cancel_outbound: Callable[[bytes], None] | None,
    *,
    value: int,
    unit: str,
    now: float,
) -> int:
    """Delete local LXMF message rows older than the retention window.

    Does not contact peers; only removes rows from the local database.
    """
    cutoff = local_message_retention_cutoff_ts(now, value, unit)
    return purge_messages_before_cutoff(messages, cancel_outbound, cutoff)
