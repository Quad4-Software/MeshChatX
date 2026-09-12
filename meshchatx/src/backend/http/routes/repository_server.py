# SPDX-License-Identifier: 0BSD
"""HTTP routes: repository_server."""

from __future__ import annotations

import asyncio

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_error_from_exception,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    read_field_limited,
    read_json_limited,
)


def register_repository_server_routes(routes, app):

    # repository server (wheels + uploads, and optional in-process plain HTTP)
    @routes.get(API_V1_PREFIX + "/repository-server/status")
    async def repository_server_status(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        return web.json_response(mgr.status())

    @routes.get(API_V1_PREFIX + "/repository-server/list")
    async def repository_server_list(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        return web.json_response(mgr.list_entries())

    @routes.post(API_V1_PREFIX + "/repository-server/upload")
    async def repository_server_upload(request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        try:
            reader = await request.multipart()
            field = await reader.next()
            if not field or field.name != "file":
                return http_bad_request("No file field in multipart request")
            filename = field.filename or "upload.bin"
            data = await read_field_limited(
                field,
                UPLOAD_LIMITS["repository_upload"],
            )
            ok, err = mgr.save_upload(filename, data)
            if not ok:
                return http_bad_request(err, success=False)
            return web.json_response({"success": True})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    @routes.delete(API_V1_PREFIX + "/repository-server/upload/{name}")
    async def repository_server_delete_upload(request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        name = request.match_info.get("name") or ""
        ok, err = mgr.delete_upload(name)
        if not ok:
            code = 404 if err == "not_found" else 400
            return http_error(code, err, success=False)
        return web.json_response({"success": True})

    @routes.post(API_V1_PREFIX + "/repository-server/http/start")
    async def repository_server_http_start(request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
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
                return http_bad_request("invalid_port", ok=False)
        try:
            result = await asyncio.to_thread(
                mgr.start_http_server,
                str(host).strip() if host is not None else None,
                port_int,
            )
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    @routes.post(API_V1_PREFIX + "/repository-server/http/stop")
    async def repository_server_http_stop(_request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        try:
            result = await asyncio.to_thread(mgr.stop_http_server)
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    @routes.post(API_V1_PREFIX + "/repository-server/http/restart")
    async def repository_server_http_restart(request):
        mgr = app.repository_server_manager
        if not mgr:
            return http_unavailable("Unavailable")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
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
                return http_bad_request("invalid_port", ok=False)
        try:
            result = await asyncio.to_thread(
                mgr.restart_http_server,
                str(host).strip() if host is not None else None,
                port_int,
            )
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # export docs
