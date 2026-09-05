# SPDX-License-Identifier: 0BSD
"""HTTP routes: map tiles."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.map._names import *  # noqa: F403, F405


def register_map_tiles_routes(routes, app):

    # get offline map metadata
    @routes.get("/api/v1/map/offline")
    async def get_map_offline_metadata(request):
        metadata = app.map_manager.get_metadata()
        if not metadata:
            app.map_manager.ensure_starter_mbtiles()
            metadata = app.map_manager.get_metadata()
        if metadata:
            return web.json_response(metadata)
        return web.json_response({"loaded": False})

    @routes.post("/api/v1/map/mbtiles/restore-starter")
    async def restore_starter_mbtiles(request):
        path = app.map_manager.ensure_starter_mbtiles(force_restore=True)
        if not path:
            return web.json_response(
                {"error": "Could not restore starter tiles"}, status=500
            )
        return web.json_response(
            {
                "message": "Starter tiles restored",
                "path": path,
                "metadata": app.map_manager.get_metadata(),
            },
        )

    # get map tile

    # get map tile
    @routes.get("/api/v1/map/tiles/{z}/{x}/{y}")
    async def get_map_tile(request):
        try:
            z = int(request.match_info.get("z"))
            x = int(request.match_info.get("x"))
            y_str = request.match_info.get("y")
            # remove .png if present
            y_str = y_str.removesuffix(".png")
            y = int(y_str)

            tile_data = app.map_manager.get_tile(z, x, y)
            if tile_data:
                return web.Response(body=tile_data, content_type="image/png")

            # If tile not found, return a transparent 1x1 PNG instead of 404
            # to avoid browser console errors in offline mode.
            return web.Response(body=TRANSPARENT_TILE, content_type="image/png")
        except Exception:
            return web.Response(status=400)

    # list available MBTiles files

    # list available MBTiles files
    @routes.get("/api/v1/map/mbtiles")
    async def list_mbtiles(request):
        return web.json_response(app.map_manager.list_mbtiles())

    # delete an MBTiles file

    # delete an MBTiles file
    @routes.delete("/api/v1/map/mbtiles/{filename}")
    async def delete_mbtiles(request):
        filename = request.match_info.get("filename")
        if app.map_manager.delete_mbtiles(filename):
            return web.json_response({"message": "File deleted"})
        return web.json_response({"error": "File not found"}, status=404)

    # set active MBTiles file

    # set active MBTiles file
    @routes.post("/api/v1/map/mbtiles/active")
    async def set_active_mbtiles(request):
        data = await request.json()
        filename = data.get("filename")
        if not filename:
            app.config.map_offline_path.set(None)
            app.config.map_offline_enabled.set(False)
            return web.json_response({"message": "Offline map disabled"})

        mbtiles_dir = app.map_manager.get_mbtiles_dir()
        safe_name = os.path.basename(filename)
        file_path = os.path.join(mbtiles_dir, safe_name)
        if not is_path_within_dir(file_path, mbtiles_dir):
            return web.json_response({"error": "Invalid filename"}, status=400)
        if os.path.exists(file_path):
            app.map_manager.close()
            app.config.map_offline_path.set(file_path)
            app.config.map_offline_enabled.set(True)
            return web.json_response(
                {
                    "message": "Active map updated",
                    "metadata": app.map_manager.get_metadata(),
                },
            )
        return web.json_response({"error": "File not found"}, status=404)

    # map drawings

    # upload offline map
    @routes.post("/api/v1/map/offline")
    async def upload_map_offline(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response({"error": "No file field"}, status=400)

            filename = os.path.basename(field.filename or "")
            if not is_mbtiles_filename(filename):
                return web.json_response(
                    {"error": "Invalid file format, must be .mbtiles"},
                    status=400,
                )

            mbtiles_dir = app.map_manager.get_mbtiles_dir()
            if not os.path.exists(mbtiles_dir):
                os.makedirs(mbtiles_dir)

            dest_path = os.path.join(mbtiles_dir, filename)
            if not is_path_within_dir(dest_path, mbtiles_dir):
                return web.json_response(
                    {"error": "Invalid filename"},
                    status=400,
                )

            size = 0
            with open(dest_path, "wb") as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)

            # close old connection and clear cache before update
            app.map_manager.close()

            # update config
            app.config.map_offline_path.set(dest_path)
            app.config.map_offline_enabled.set(True)

            # validate
            metadata = app.map_manager.get_metadata()
            if not metadata:
                # delete if invalid
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                app.config.map_offline_path.set(None)
                app.config.map_offline_enabled.set(False)
                return web.json_response(
                    {
                        "error": "Invalid MBTiles file or unsupported format (vector maps not supported)",
                    },
                    status=400,
                )

            return web.json_response(
                {
                    "message": "Map uploaded successfully",
                    "metadata": metadata,
                },
            )
        except Exception as e:
            RNS.log(f"Error uploading map: {e}", RNS.LOG_ERROR)
            return web.json_response({"error": str(e)}, status=500)

    # start map export
