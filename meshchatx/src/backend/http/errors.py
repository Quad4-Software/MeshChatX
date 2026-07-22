# SPDX-License-Identifier: 0BSD

"""Shared HTTP JSON error helpers for thin route handlers.

Conventions match backend docs: 400 for bad input, 503 for retryable
unavailability, 500 only for unexpected failures. Prefer adopting these
helpers when a handler is already thin. Do not refactor fat handlers only
to call these in a mechanical move change.
"""

from __future__ import annotations

from aiohttp import web


def http_bad_request(message: str, **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=400)


def http_unavailable(message: str, **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=503)


def http_unexpected(message: str = "Unexpected server error", **extra):
    payload = {"error": message, **extra}
    return web.json_response(payload, status=500)
