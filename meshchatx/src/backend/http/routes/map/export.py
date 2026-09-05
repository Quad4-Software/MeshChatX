# SPDX-License-Identifier: 0BSD
"""HTTP routes: map export."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.map._names import *  # noqa: F403, F405


def register_map_export_routes(routes, app):

    # start map export
    @routes.post("/api/v1/map/export")
    async def start_map_export(request):
        try:
            data = await request.json()
            bbox = data.get("bbox")  # [min_lon, min_lat, max_lon, max_lat]
            min_zoom = int(data.get("min_zoom", 0))
            max_zoom = int(data.get("max_zoom", 10))
            name = data.get("name", "Exported Map")

            if not bbox or len(bbox) != 4:
                return web.json_response({"error": "Invalid bbox"}, status=400)

            app._require_outbound_http("map tile export")

            tile_count = app.map_manager.count_export_tiles(
                bbox,
                min_zoom,
                max_zoom,
            )
            if tile_count > MAX_EXPORT_TILES:
                return web.json_response(
                    {
                        "error": (
                            f"Export would download {tile_count} tiles; "
                            f"maximum allowed is {MAX_EXPORT_TILES}. "
                            "Shrink the area or lower max zoom."
                        ),
                    },
                    status=400,
                )

            export_id = secrets.token_hex(8)
            app.map_manager.start_export(export_id, bbox, min_zoom, max_zoom, name)

            return web.json_response({"export_id": export_id})
        except OutboundHttpBlockedError as e:
            return web.json_response({"error": str(e)}, status=403)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # get map export status

    # get map export status
    @routes.get("/api/v1/map/export/{export_id}")
    async def get_map_export_status(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status:
            return web.json_response(status)
        return web.json_response({"error": "Export not found"}, status=404)

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
        return web.json_response(
            {"error": "File not ready or not found"},
            status=404,
        )

    # cancel/delete map export

    # cancel/delete map export
    @routes.delete("/api/v1/map/export/{export_id}")
    async def delete_map_export(request):
        export_id = request.match_info.get("export_id")
        if app.map_manager.cancel_export(export_id):
            return web.json_response({"message": "Export cancelled/deleted"})
        return web.json_response({"error": "Export not found"}, status=404)
