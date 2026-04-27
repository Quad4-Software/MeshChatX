# SPDX-License-Identifier: 0BSD
"""Local-only age-based deletion of stored LXMF rows (this device, no network signal)."""

import logging
from collections.abc import Callable

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
    hashes = messages.list_message_hashes_with_timestamp_before(cutoff)
    if not hashes:
        return 0
    if cancel_outbound is not None:
        for h in hashes:
            if not h or len(h) % 2 != 0:
                continue
            try:
                cancel_outbound(bytes.fromhex(h))
            except Exception as exc:  # noqa: BLE001
                log.debug("local_message_retention cancel_outbound: %s", exc)
    messages.delete_lxmf_messages_by_hashes(hashes)
    messages.prune_conversation_metadata_for_peers_with_no_messages()
    return len(hashes)
