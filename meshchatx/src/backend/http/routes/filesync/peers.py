# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync peers."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *  # noqa: F403


def register_filesync_peers_routes(routes: Any, app: Any) -> None:
    (_filesync_require_handler,) = make_filesync_helpers(app)

    @routes.get("/api/v1/filesync/peers")
    async def filesync_peers(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response({"peers": app.rns_filesync_handler.list_peers()})

    @routes.post("/api/v1/filesync/connect")
    async def filesync_connect(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        identity_hash = data.get("identity_hash", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.connect_peer,
                identity_hash,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "connect failed"), **result},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/disconnect")
    async def filesync_disconnect(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        peer_id = data.get("peer_id", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.disconnect_peer,
                peer_id,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "disconnect failed")},
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/browse")
    async def filesync_browse(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        peer_id = data.get("peer_id", "")
        timeout = data.get("timeout", 10.0)
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.browse_peer,
                peer_id,
                timeout,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {
                    "message": result.get("error", "browse failed"),
                    "files": result.get("files", []),
                },
                status=400,
            )
        return web.json_response(result)

    @routes.post("/api/v1/filesync/download")
    async def filesync_download(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        peer_id = data.get("peer_id", "")
        path = data.get("path", "")
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.download_file,
                peer_id,
                path,
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "download failed"), **result},
                status=400,
            )
        return web.json_response(result)
