# SPDX-License-Identifier: 0BSD
"""HTTP routes: map export."""

from __future__ import annotations

import math

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.map._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.map_manager import MAX_EXPORT_ZOOM


def register_map_export_routes(routes, app):

    # start map export
    @routes.post("/api/v1/map/export")
    async def start_map_export(request):
        try:
            data = await read_json_limited(request)
            if not isinstance(data, dict):
                return http_bad_request("Invalid body")
            bbox = data.get("bbox")  # [min_lon, min_lat, max_lon, max_lat]
            try:
                min_zoom = int(data.get("min_zoom", 0))
                max_zoom = int(data.get("max_zoom", 10))
            except (TypeError, ValueError):
                return http_bad_request("Invalid zoom levels")
            name = data.get("name", "Exported Map")

            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                return http_bad_request("Invalid bbox")
            try:
                bbox = [float(v) for v in bbox]
            except (TypeError, ValueError):
                return http_bad_request("Invalid bbox")
            if not all(math.isfinite(v) for v in bbox):
                return http_bad_request("Invalid bbox")
            if not (0 <= min_zoom <= max_zoom <= MAX_EXPORT_ZOOM):
                return http_bad_request(
                    f"Invalid zoom range; "
                    f"allowed is 0 <= min_zoom <= max_zoom <= "
                    f"{MAX_EXPORT_ZOOM}."
                )

            app._require_outbound_http("map tile export")

            tile_count = app.map_manager.count_export_tiles(
                bbox,
                min_zoom,
                max_zoom,
                limit=MAX_EXPORT_TILES,
            )
            if tile_count > MAX_EXPORT_TILES:
                return http_bad_request(
                    f"Export would download more than "
                    f"{MAX_EXPORT_TILES} tiles; "
                    f"maximum allowed is {MAX_EXPORT_TILES}. "
                    "Shrink the area or lower max zoom."
                )

            export_id = secrets.token_hex(8)
            app.map_manager.start_export(export_id, bbox, min_zoom, max_zoom, name)

            return web.json_response({"export_id": export_id})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except OutboundHttpBlockedError as e:
            return http_forbidden(str(e))
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # get map export status

    # get map export status
    @routes.get("/api/v1/map/export/{export_id}")
    async def get_map_export_status(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status:
            return web.json_response(status)
        return http_not_found("Export not found")

    # download exported map

    # download exported map
    @routes.get("/api/v1/map/export/{export_id}/download")
    async def download_map_export(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status and status.get("status") == "completed":
            file_path = status.get("file_path")
            if os.path.exists(file_path):
                return web.FileResponse(
                    path=file_path,
                    headers={
                        "Content-Disposition": f'attachment; filename="map_export_{export_id}.mbtiles"',
                    },
                )
        return http_not_found("File not ready or not found")

    # cancel/delete map export

    # cancel/delete map export
    @routes.delete("/api/v1/map/export/{export_id}")
    async def delete_map_export(request):
        export_id = request.match_info.get("export_id")
        if app.map_manager.cancel_export(export_id):
            return web.json_response({"message": "Export cancelled/deleted"})
        return http_not_found("Export not found")

