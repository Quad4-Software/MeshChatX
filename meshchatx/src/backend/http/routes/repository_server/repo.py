# SPDX-License-Identifier: 0BSD
"""HTTP routes: repository_server/repo."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.repository_server._names import *  # noqa: F403


def register_repository_server_repo_routes(routes: Any, app: Any) -> None:

    # repository server (wheels + uploads, and optional in-process plain HTTP)

    @routes.get("/api/v1/repository-server/status")
    async def repository_server_status(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        return web.json_response(mgr.status())

    @routes.get("/api/v1/repository-server/list")
    async def repository_server_list(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        return web.json_response(mgr.list_entries())

    @routes.post("/api/v1/repository-server/upload")
    async def repository_server_upload(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            reader = await request.multipart()
            field = await reader.next()
            if not field or field.name != "file":
                return web.json_response(
                    {"error": "No file field in multipart request"},
                    status=400,
                )
            filename = field.filename or "upload.bin"
            data = await field.read()
            ok, err = mgr.save_upload(filename, data)
            if not ok:
                return web.json_response(
                    {"success": False, "error": err},
                    status=400,
                )
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.delete("/api/v1/repository-server/upload/{name}")
    async def repository_server_delete_upload(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        name = request.match_info.get("name") or ""
        ok, err = mgr.delete_upload(name)
        if not ok:
            code = 404 if err == "not_found" else 400
            return web.json_response({"success": False, "error": err}, status=code)
        return web.json_response({"success": True})

    @routes.post("/api/v1/repository-server/http/start")
    async def repository_server_http_start(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        host = data.get("host")
        port = data.get("port")
        port_int = None
        if port is not None:
            try:
                port_int = int(port)
            except (TypeError, ValueError):
                return web.json_response(
                    {"ok": False, "error": "invalid_port"},
                    status=400,
                )
        try:
            result = await asyncio.to_thread(
                mgr.start_http_server,
                str(host).strip() if host is not None else None,
                port_int,
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/repository-server/http/stop")
    async def repository_server_http_stop(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            result = await asyncio.to_thread(mgr.stop_http_server)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/repository-server/http/restart")
    async def repository_server_http_restart(request):
        mgr = app.repository_server_manager
        if not mgr:
            return web.json_response({"error": "Unavailable"}, status=503)
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        host = data.get("host")
        port = data.get("port")
        port_int = None
        if port is not None:
            try:
                port_int = int(port)
            except (TypeError, ValueError):
                return web.json_response(
                    {"ok": False, "error": "invalid_port"},
                    status=400,
                )
        try:
            result = await asyncio.to_thread(
                mgr.restart_http_server,
                str(host).strip() if host is not None else None,
                port_int,
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
