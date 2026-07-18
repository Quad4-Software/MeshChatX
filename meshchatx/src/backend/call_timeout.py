# SPDX-License-Identifier: 0BSD
"""Clamp helpers for telephone call initiation timeouts."""

from __future__ import annotations

DEFAULT_CALL_TIMEOUT_SECONDS = 15
MIN_CALL_TIMEOUT_SECONDS = 1
MAX_CALL_TIMEOUT_SECONDS = 120


def clamp_call_timeout_seconds(
    raw,
    *,
    default: int = DEFAULT_CALL_TIMEOUT_SECONDS,
    min_s: int = MIN_CALL_TIMEOUT_SECONDS,
    max_s: int = MAX_CALL_TIMEOUT_SECONDS,
) -> int:
    """Parse and clamp a call timeout query value.

    Invalid values fall back to default. Result is always within [min_s, max_s].
    """
    try:
        timeout_seconds = int(raw) if raw is not None else int(default)
    except (TypeError, ValueError):
        timeout_seconds = int(default)
    return max(int(min_s), min(timeout_seconds, int(max_s)))
