# SPDX-License-Identifier: 0BSD
"""Experimental WebTransport sidecar (optional aioquic). Shares live client bus."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

WT_PATH = "/meshchatx-live"
WT_REASON_DISABLED = "disabled"
WT_REASON_HTTP_ONLY = "http_only"
WT_REASON_AIOQUIC_MISSING = "aioquic_missing"
WT_REASON_BIND_FAILED = "bind_failed"
WT_REASON_LANDLOCK_UDP = "landlock_udp"
WT_REASON_UNSUPPORTED = "unsupported_platform"
WT_REASON_LISTENER_PENDING = "listener_pending"

CLOSED_REASONS = frozenset(
    {
        WT_REASON_DISABLED,
        WT_REASON_HTTP_ONLY,
        WT_REASON_AIOQUIC_MISSING,
        WT_REASON_BIND_FAILED,
        WT_REASON_LANDLOCK_UDP,
        WT_REASON_UNSUPPORTED,
        WT_REASON_LISTENER_PENDING,
    },
)


def env_webtransport_enabled() -> bool:
    return os.environ.get("MESHCHAT_EXPERIMENTAL_WEBTRANSPORT", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def aioquic_available() -> bool:
    try:
        import aioquic  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


class WtClientAdapter:
    """Minimal send_str/close surface matching aiohttp WS clients for fan-out."""

    __slots__ = ("_closed", "_queue", "transport_kind")

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._closed = False
        self.transport_kind = "webtransport"

    async def send_str(self, data: str) -> None:
        if self._closed:
            raise RuntimeError("wt client closed")
        await self._queue.put(data)

    async def close(self, code: int = 1000) -> None:
        del code
        self._closed = True
        await self._queue.put(None)

    async def recv_outbound(self) -> str | None:
        return await self._queue.get()


class WebTransportSidecarState:
    """Runtime advertisement for /api/v1/status and debug."""

    __slots__ = (
        "cert_sha256_b64",
        "enabled_intent",
        "listen_host",
        "listen_port",
        "reason",
        "server_available",
        "task",
        "url",
    )

    def __init__(self) -> None:
        self.server_available = False
        self.reason: str | None = WT_REASON_DISABLED
        self.url: str | None = None
        self.cert_sha256_b64: str | None = None
        self.listen_host: str | None = None
        self.listen_port: int | None = None
        self.enabled_intent = False
        self.task: asyncio.Task | None = None

    def status_dict(self) -> dict[str, Any]:
        return {
            "experimental": True,
            "server_available": bool(self.server_available),
            "url": self.url,
            "cert_sha256_b64": self.cert_sha256_b64,
            "reason": self.reason if not self.server_available else None,
            "enabled_intent": bool(self.enabled_intent),
            "listen_host": self.listen_host,
            "listen_port": self.listen_port,
            "client_probe_supported": True,
        }


def build_webtransport_status(
    *,
    https_enabled: bool,
    sidecar_enabled: bool,
    env_enabled: bool,
    landlock_active: bool = False,
) -> WebTransportSidecarState:
    """Compute availability without binding. Used for status and startup decisions."""
    state = WebTransportSidecarState()
    state.enabled_intent = bool(sidecar_enabled or env_enabled)
    if not https_enabled:
        state.reason = WT_REASON_HTTP_ONLY
        return state
    if not state.enabled_intent:
        state.reason = WT_REASON_DISABLED
        return state
    if landlock_active:
        # UDP often blocked until rules allow it. Report clearly; bind may still try.
        state.reason = WT_REASON_LANDLOCK_UDP
    if not aioquic_available():
        state.reason = WT_REASON_AIOQUIC_MISSING
        return state
    # Not bound yet
    state.reason = WT_REASON_DISABLED if not state.enabled_intent else None
    return state


async def try_start_webtransport_sidecar(app) -> WebTransportSidecarState:
    """Start optional QUIC listener. Never raises into aiohttp boot."""
    state = getattr(app, "webtransport_state", None)
    if state is None:
        state = WebTransportSidecarState()
        app.webtransport_state = state

    https_enabled = bool(getattr(app, "use_https", False))
    cfg = None
    try:
        ctx = getattr(app, "current_context", None)
        cfg = getattr(ctx, "config", None) if ctx else None
        if cfg is None:
            cfg = getattr(app, "config", None)
    except Exception:
        cfg = None

    sidecar_cfg = False
    if cfg is not None:
        try:
            getter = getattr(cfg, "webtransport_sidecar_enabled", None)
            if getter is not None:
                sidecar_cfg = bool(getter.get())
        except Exception:
            sidecar_cfg = False

    env_on = env_webtransport_enabled()
    landlock = bool(getattr(app, "landlock_active", False))
    draft = build_webtransport_status(
        https_enabled=https_enabled,
        sidecar_enabled=sidecar_cfg,
        env_enabled=env_on,
        landlock_active=landlock,
    )
    state.enabled_intent = draft.enabled_intent
    if not draft.enabled_intent:
        state.server_available = False
        state.reason = WT_REASON_DISABLED
        return state
    if not https_enabled:
        state.server_available = False
        state.reason = WT_REASON_HTTP_ONLY
        return state
    if not aioquic_available():
        state.server_available = False
        state.reason = WT_REASON_AIOQUIC_MISSING
        return state

    storage = getattr(app, "storage_path", None) or getattr(app, "storage_dir", None)
    if not storage:
        state.server_available = False
        state.reason = WT_REASON_UNSUPPORTED
        return state

    try:
        from meshchatx.src.backend.webtransport_cert import (
            ensure_webtransport_cert_pair,
        )

        _cert, _key, sha_b64 = ensure_webtransport_cert_pair(storage)
        state.cert_sha256_b64 = sha_b64
    except Exception:
        logger.exception("webtransport cert generation failed")
        state.server_available = False
        state.reason = WT_REASON_BIND_FAILED
        return state

    host = getattr(app, "listen_host", None) or "127.0.0.1"
    port = int(getattr(app, "listen_port", 0) or 0)
    if port <= 0:
        state.server_available = False
        state.reason = WT_REASON_BIND_FAILED
        return state

    # Cert + URL are prepared for experimental clients. Full aioquic H3
    # WebTransport accept is not started yet, so do not claim server_available
    # (avoids Auto-mode connect timeouts on every shell boot).
    try:
        state.listen_host = host
        state.listen_port = port
        display_host = "127.0.0.1" if host in ("0.0.0.0", "::", "[::]") else host
        state.url = f"https://{display_host}:{port}{WT_PATH}"
        state.server_available = False
        state.reason = WT_REASON_LISTENER_PENDING
        logger.info(
            "WebTransport experimental endpoint prepared at %s (listener pending)",
            state.url,
        )
    except Exception:
        logger.exception("webtransport sidecar advertise failed")
        state.server_available = False
        state.reason = WT_REASON_BIND_FAILED
        if landlock:
            state.reason = WT_REASON_LANDLOCK_UDP

    return state


def wt_frame_encode(obj: dict[str, Any]) -> bytes:
    return (json.dumps(obj, default=str) + "\n").encode("utf-8")


def wt_frame_feed(
    buffer: str, chunk: str, *, max_chars: int = 1024 * 1024
) -> tuple[list[dict], str, list[str]]:
    """Server-side newline JSON framing (mirrors frontend feedWtJsonLines)."""
    errors: list[str] = []
    buf = (buffer or "") + (chunk or "")
    if len(buf) > max_chars * 2:
        return [], "", ["frame_overflow"]
    objects: list[dict] = []
    while True:
        idx = buf.find("\n")
        if idx < 0:
            break
        line = buf[:idx]
        buf = buf[idx + 1 :]
        if not line:
            continue
        if len(line) > max_chars:
            errors.append("line_too_large")
            continue
        if "\0" in line:
            errors.append("embedded_nul")
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            errors.append("invalid_json")
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
        else:
            errors.append("not_object")
    return objects, buf, errors
