# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync status and lifecycle."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *  # noqa: F403


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
        with contextlib.suppress(Exception):
            data = await request.json()
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
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "failed to start")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/stop")
    async def filesync_stop(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.stop)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        return web.json_response(result)

    @routes.post("/api/v1/filesync/announce")
    async def filesync_announce(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        try:
            result = await asyncio.to_thread(app.rns_filesync_handler.announce_now)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "announce failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.patch("/api/v1/filesync/settings")
    async def filesync_settings(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.update_settings,
                sync_directory=data.get("sync_directory"),
                monitor=data.get("monitor"),
                announce_interval=data.get("announce_interval"),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "settings update failed")},
                status=400,
            )
        return web.json_response(result)
