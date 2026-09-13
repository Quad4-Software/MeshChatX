# SPDX-License-Identifier: 0BSD

"""Shared HTTP JSON error helpers for thin route handlers.

Canonical error shape: {"error": str, "code": str, "message": str}.
"error" is the human-readable message, "code" a stable machine string,
and "message" a compatibility alias of "error" for callers written
against the older payload. Extra keys merge via **extra.

Conventions match backend docs: 400 for bad input, 503 for retryable
unavailability, 500 only for unexpected failures. Prefer adopting these
helpers when a handler is already thin. Do not refactor fat handlers only
to call these in a mechanical move change.
"""

from __future__ import annotations

# pyright: strict
import sqlite3
from typing import Any

from aiohttp import web

from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable
from meshchatx.src.path_utils import PathJailError

_PATH_JAIL_STATUS = {
    "required": 400,
    "invalid": 400,
    "absolute": 400,
    "escape": 403,
    "reserved": 403,
    "forbidden": 403,
    "not_found": 404,
}


def _error_payload(message: str, code: str, extra: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": message, "code": code, "message": message}
    payload.update(extra)
    return payload


def http_error(
    status: int, message: str, *, code: str | None = None, **extra: Any
) -> web.Response:
    """Generic error response for statuses without a dedicated helper."""
    return web.json_response(
        _error_payload(message, code or f"http_{status}", extra),
        status=status,
    )


def http_bad_request(
    message: str, *, code: str = "bad_request", **extra: Any
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=400)


def http_unauthorized(
    message: str = "Authentication required",
    *,
    code: str = "auth_required",
    **extra: Any,
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=401)


def http_forbidden(
    message: str = "Not allowed", *, code: str = "forbidden", **extra: Any
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=403)


def http_not_found(
    message: str = "Not found", *, code: str = "not_found", **extra: Any
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=404)


def http_conflict(
    message: str, *, code: str = "conflict", **extra: Any
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=409)


def http_payload_too_large(
    message: str = "Upload exceeds size limit",
    *,
    code: str = "payload_too_large",
    **extra: Any,
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=413)


def http_unavailable(
    message: str, *, code: str = "unavailable", **extra: Any
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=503)


def http_unexpected(
    message: str = "Unexpected server error", *, code: str = "unexpected", **extra: Any
) -> web.Response:
    return web.json_response(_error_payload(message, code, extra), status=500)


def http_error_from_exception(
    exc: BaseException,
    *,
    fallback_status: int = 400,
    key: str = "error",
    extra: dict[str, Any] | None = None,
) -> web.Response:
    """Map an exception to a JSON error response without leaking internals.

    PathJailError reasons map to 400/403/404 and its messages are safe to
    echo (they never embed paths). ValueError messages pass through since
    this codebase treats them as user-facing. OSError and anything else
    get a generic message so absolute paths, errno details, and stack
    internals stay server-side; log the real exception at the call site.
    extra merges fixed keys into the payload (for example
    {"status": "error"} on routes that use that shape).
    """
    payload: dict[str, Any] = dict(extra) if extra else {}

    def respond(status: int, message: str) -> web.Response:
        base = _error_payload(message, f"http_{status}", {})
        if key not in base:
            base[key] = message
        return web.json_response({**base, **payload}, status=status)

    if isinstance(exc, PathJailError):
        return respond(_PATH_JAIL_STATUS.get(exc.reason, 400), str(exc))
    if isinstance(exc, FileNotFoundError):
        return respond(404, "Not found")
    if isinstance(exc, PermissionError):
        return respond(403, "Not allowed")
    if isinstance(exc, ValueError):
        return respond(400, str(exc))
    if isinstance(exc, sqlite3.Error) and sqlite_error_is_retryable(exc):
        return respond(503, "Database temporarily unavailable, retry")
    if isinstance(exc, OSError):
        return respond(500, "Internal server error")
    return respond(fallback_status, "Request failed")
