# SPDX-License-Identifier: 0BSD
"""Backoff policy for periodic outbound telemetry requests.

A tracked peer that never answers should not be polled on its base
interval forever: each unanswered request doubles the effective interval
up to a daily cap, and after a bounded number of unanswered requests the
peer is skipped until a response resets the counter.
"""

from __future__ import annotations

# Upper bound for the backed-off request interval.
TELEMETRY_REQUEST_MAX_INTERVAL_SECONDS = 24 * 60 * 60

# Unanswered requests after which a tracked peer is paused entirely. The
# row stays tracked, so a telemetry response resets the counter and
# re-arms the loop without user intervention.
TELEMETRY_REQUEST_MAX_UNANSWERED = 24


def effective_request_interval(base_interval_seconds, unanswered_count) -> int:
    try:
        base = max(1, int(base_interval_seconds))
    except (TypeError, ValueError):
        base = 60
    try:
        count = max(0, int(unanswered_count))
    except (TypeError, ValueError):
        count = 0
    shift = min(count, 20)
    return min(
        base * (1 << shift),
        TELEMETRY_REQUEST_MAX_INTERVAL_SECONDS,
    )


def is_request_paused(unanswered_count) -> bool:
    try:
        return int(unanswered_count or 0) >= TELEMETRY_REQUEST_MAX_UNANSWERED
    except (TypeError, ValueError):
        return False
