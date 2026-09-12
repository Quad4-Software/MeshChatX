# SPDX-License-Identifier: 0BSD

"""Shared HTTP JSON error helpers for thin route handlers.

Conventions match backend docs: 400 for bad input, 503 for retryable
unavailability, 500 only for unexpected failures. Prefer adopting these
helpers when a handler is already thin. Do not refactor fat handlers only
to call these in a mechanical move change.
"""

from __future__ import annotations

from aiohttp import web

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


def http_bad_request(message: str, **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=400)


def http_forbidden(message: str = "Not allowed", **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=403)


def http_not_found(message: str = "Not found", **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=404)


def http_payload_too_large(message: str = "Upload exceeds size limit", **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=413)


def http_unavailable(message: str, **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=503)


def http_unexpected(message: str = "Unexpected server error", **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=500)


def http_error_from_exception(
    exc: BaseException,
    *,
    fallback_status: int = 400,
    key: str = "error",
    extra: dict | None = None,
):
    """Map an exception to a JSON error response without leaking internals.

    PathJailError reasons map to 400/403/404 and its messages are safe to
    echo (they never embed paths). ValueError messages pass through since
    this codebase treats them as user-facing. OSError and anything else
    get a generic message so absolute paths, errno details, and stack
    internals stay server-side; log the real exception at the call site.
    extra merges fixed keys into the payload (for example
    {"status": "error"} on routes that use that shape).
    """
    payload = dict(extra) if extra else {}

    def respond(status: int, message: str):
        return web.json_response({**payload, key: message}, status=status)

    if isinstance(exc, PathJailError):
        return respond(_PATH_JAIL_STATUS.get(exc.reason, 400), str(exc))
    if isinstance(exc, FileNotFoundError):
        return respond(404, "Not found")
    if isinstance(exc, PermissionError):
        return respond(403, "Not allowed")
    if isinstance(exc, ValueError):
        return respond(400, str(exc))
    if isinstance(exc, OSError):
        return respond(500, "Internal server error")
    return respond(fallback_status, "Request failed")
