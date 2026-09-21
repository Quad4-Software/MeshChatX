# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync status and lifecycle."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_payload_too_large,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_filesync_status_routes(routes: Any, app: Any) -> None:
    (_filesync_require_handler,) = make_filesync_helpers(app)

    @routes.get("/api/v1/filesync/status")
    async def filesync_status(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response(app.rns_filesync_handler.get_status())

    @routes.post("/api/v1/filesync/start")
    async def filesync_start(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = {}
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.start,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "failed to start"))
        return web.json_response(result)

    @routes.post("/api/v1/filesync/stop")
    async def filesync_stop(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.stop)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        return web.json_response(result)

    @routes.post("/api/v1/filesync/announce")
    async def filesync_announce(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.announce_now)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "announce failed"))
        return web.json_response(result)

    @routes.patch("/api/v1/filesync/settings")
    async def filesync_settings(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.update_settings,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "settings update failed"))
        return web.json_response(result)
