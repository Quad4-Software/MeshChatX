# SPDX-License-Identifier: 0BSD

"""Thin Python backend for the bundled mcx-hello example plugin.

Host manager capabilities do the real work. This module keeps activate/invoke
hooks so the package exercises the Python plugin runtime.
"""

from __future__ import annotations

from typing import Any


def activate(host) -> None:
    host.storage_set("activated", "1")
    host.log("mcx-hello backend activated")


def deactivate() -> None:
    return None


def invoke(method: str, args: dict[str, Any], host=None) -> Any:
    if host is None:
        host = args
        args = method if isinstance(method, dict) else {}
        method = "invoke"
    args = args or {}
    if method == "ping":
        return {"ok": True, "activated": host.storage_get("activated")}
    if method == "counter":
        raw = host.storage_get("counter") or "0"
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 0
        if args.get("op") == "inc":
            value += 1
            host.storage_set("counter", str(value))
        return {"value": value}
    if method == "call":
        capability = args.get("capability")
        if not isinstance(capability, str) or not capability:
            raise ValueError("capability is required")
        return host.call_manager(capability, args.get("args") or {})
    raise ValueError(f"unknown method: {method}")


def on_hook(hook: str, payload: dict[str, Any], host) -> Any:
    return None
