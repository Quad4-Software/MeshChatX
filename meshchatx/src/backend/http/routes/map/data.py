# SPDX-License-Identifier: 0BSD
"""HTTP routes: map data."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.map._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_not_found,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)



def register_map_data_routes(routes, app):

    @routes.get("/api/v1/map/data/status")
    async def map_data_status(_request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        return web.json_response(app.map_data_manager.status())

    @routes.get("/api/v1/map/data/published")
    async def map_data_published(_request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        return web.json_response({"maps": app.map_data_manager.list_published()})

    @routes.get("/api/v1/map/data/heard")
    async def map_data_heard(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        query = request.query.get("search") or request.query.get("q")
        try:
            limit = int(request.query.get("limit") or 250)
        except (TypeError, ValueError):
            limit = 250
        limit = max(1, min(limit, 2500))
        return web.json_response(
            {"announces": app.map_data_manager.list_heard(query=query, limit=limit)},
        )

    @routes.post("/api/v1/map/data/publish")
    async def map_data_publish(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        name = str(data.get("name") or "map")
        hinted = data.get("format")
        raw_b64 = data.get("data_b64") or data.get("content_b64")
        if not isinstance(raw_b64, str) or not raw_b64.strip():
            return http_bad_request("missing_data")
        max_bytes = 512 * 1024
        try:
            configured = app.map_data_manager._cfg_max_bytes()
        except (TypeError, ValueError, AttributeError):
            configured = None
        if isinstance(configured, int) and configured >= 1:
            max_bytes = configured
        if len(raw_b64) > (max_bytes * 4 // 3) + 8:
            return http_bad_request("file_too_large")
        try:
            payload = base64.b64decode(raw_b64, validate=True)
        except (binascii.Error, ValueError):
            return http_bad_request("invalid_data")
        try:
            result = app.map_data_manager.publish_bytes(
                payload,
                name=name,
                hinted_format=hinted,
            )
        except MapDataError as exc:
            return http_bad_request(exc.code)
        except GeoValidationError as exc:
            return http_bad_request(exc.code)
        return web.json_response(result)

    @routes.delete("/api/v1/map/data/published/{map_id}")
    async def map_data_unpublish(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        map_id = request.match_info.get("map_id")
        try:
            ok = app.map_data_manager.unpublish(map_id)
        except MapDataError as exc:
            return http_bad_request(exc.code)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"deleted": True})

    @routes.post("/api/v1/map/data/announce")
    async def map_data_announce(_request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            return web.json_response(app.map_data_manager.announce())
        except MapDataError as exc:
            return http_bad_request(exc.code)

    @routes.patch("/api/v1/map/data/config")
    async def map_data_config(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        return web.json_response(
            app.map_data_manager.update_settings(
                display_name=data.get("display_name"),
                announce_enabled=data.get("announce_enabled"),
                announce_interval=data.get("announce_interval"),
            ),
        )

    @routes.post("/api/v1/map/data/catalog")
    async def map_data_catalog(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        dest = data.get("destination_hash")
        try:
            result = await app.map_data_manager.fetch_catalog(dest)
        except MapDataError as exc:
            status = 400
            if exc.code in (
                "missing_path",
                "link_failed",
                "job_timeout",
                "request_failed",
                "empty_response",
                "invalid_response",
            ):
                status = 503
            return http_error(status, exc.code)
        return web.json_response(result)

    @routes.post("/api/v1/map/data/fetch")
    async def map_data_fetch(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        dest = data.get("destination_hash")
        map_id = data.get("map_id")
        try:
            body = await app.map_data_manager.fetch_map_bytes(dest, map_id)
        except MapDataError as exc:
            status = 400
            if exc.code in (
                "missing_path",
                "link_failed",
                "job_timeout",
                "request_failed",
                "empty_response",
                "invalid_response",
            ):
                status = 503
            return http_error(status, exc.code)
        return web.json_response(
            {
                "data_b64": base64.b64encode(body).decode("ascii"),
                "size": len(body),
            },
        )

    @routes.post("/api/v1/map/data/add-overlay")
    async def map_data_add_overlay(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        dest = data.get("destination_hash")
        map_id = data.get("map_id")
        try:
            result = await app.map_data_manager.add_as_overlay(dest, map_id)
        except MapDataError as exc:
            status = 400
            if exc.code in (
                "missing_path",
                "link_failed",
                "job_timeout",
                "request_failed",
                "empty_response",
                "invalid_response",
            ):
                status = 503
            return http_error(status, exc.code)
        except OverlaySourceParseError as exc:
            return http_bad_request(exc.code)
        except GeoValidationError as exc:
            return http_bad_request(exc.code)
        return web.json_response(result)

    # MIME type fix middleware - ensures JavaScript files have correct Content-Type
