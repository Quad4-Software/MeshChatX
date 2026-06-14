# SPDX-License-Identifier: 0BSD

"""Startup memory checks before heavy backend initialization."""

from __future__ import annotations

import contextlib

import psutil

MEMORY_LOG_PREFIX = "MESHCHAT_MEMORY:"

_ABORT_AVAILABLE_MB = 150
_CRITICAL_WARN_AVAILABLE_MB = 400
_WARN_AVAILABLE_MB = 700
_LOW_TOTAL_MB = 5120
_CRITICAL_WARN_PERCENT = 90
_WARN_PERCENT = 85


def get_system_memory_snapshot() -> dict:
    """Return host memory metrics in megabytes and percent used."""
    mem = psutil.virtual_memory()
    return {
        "total_mb": mem.total / (1024**2),
        "available_mb": mem.available / (1024**2),
        "percent_used": float(mem.percent),
    }


def evaluate_startup_memory(emergency: bool = False) -> dict:
    """Classify startup memory pressure and choose a guard action."""
    snapshot = get_system_memory_snapshot()
    available_mb = snapshot["available_mb"]
    total_mb = snapshot["total_mb"]
    percent_used = snapshot["percent_used"]

    action = "ok"
    message = ""

    if available_mb < _ABORT_AVAILABLE_MB:
        action = "abort"
        message = (
            "Available memory is critically low "
            f"({available_mb:.0f} MB). Close other apps or relaunch in Emergency Mode."
        )
    elif available_mb < _CRITICAL_WARN_AVAILABLE_MB or (
        total_mb <= _LOW_TOTAL_MB and percent_used >= _CRITICAL_WARN_PERCENT
    ):
        action = "warn"
        message = (
            "Low system memory detected "
            f"({available_mb:.0f} MB available). Emergency Mode is strongly recommended."
        )
    elif available_mb < _WARN_AVAILABLE_MB or (
        total_mb <= _LOW_TOTAL_MB and percent_used >= _WARN_PERCENT
    ):
        action = "warn"
        message = (
            "System memory is limited "
            f"({available_mb:.0f} MB available). Emergency Mode is recommended on 4 GB devices."
        )

    return {
        **snapshot,
        "action": action,
        "message": message,
        "emergency_requested": emergency,
        "low_memory": action in ("abort", "warn"),
    }


def format_memory_log_line(result: dict) -> str:
    """Emit a single machine-readable startup memory line for Electron logs."""
    return (
        f"{MEMORY_LOG_PREFIX} total_mb={result['total_mb']:.1f} "
        f"available_mb={result['available_mb']:.1f} "
        f"percent_used={result['percent_used']:.1f} "
        f"action={result['action']} "
        f"emergency={str(result.get('emergency_requested', False)).lower()}"
    )


def parse_memory_log_line(text: str) -> dict | None:
    """Parse a MESHCHAT_MEMORY startup line from captured backend output."""
    if not text:
        return None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith(MEMORY_LOG_PREFIX):
            continue
        payload = line[len(MEMORY_LOG_PREFIX) :].strip()
        parsed: dict[str, str | float | bool] = {}
        for token in payload.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            if key in ("total_mb", "available_mb", "percent_used"):
                with contextlib.suppress(ValueError):
                    parsed[key] = float(value)
            elif key == "emergency":
                parsed[key] = value.lower() in ("true", "1", "yes")
            else:
                parsed[key] = value
        return parsed if parsed else None
    return None
