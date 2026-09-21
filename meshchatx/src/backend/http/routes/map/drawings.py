# SPDX-License-Identifier: 0BSD
"""HTTP routes: map drawings."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import (
    http_not_found,
    http_payload_too_large,
)

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.map._names import *  # noqa: F403
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_map_drawings_routes(routes, app):

    # map drawings
    @routes.get("/api/v1/map/drawings")
    async def get_map_drawings(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.map_drawings.get_drawings(identity_hash)
        drawings = [dict(row) for row in rows]
        return web.json_response({"drawings": drawings})

    @routes.post("/api/v1/map/drawings")
    async def save_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        name = data.get("name")
        drawing_data = data.get("data")
        app.database.map_drawings.upsert_drawing(identity_hash, name, drawing_data)
        return web.json_response({"message": "Drawing saved successfully"})

    @routes.delete("/api/v1/map/drawings/{drawing_id}")
    async def delete_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        drawing_id = request.match_info.get("drawing_id")
        deleted = app.database.map_drawings.delete_drawing(
            drawing_id,
            identity_hash,
        )
        if not deleted:
            return http_not_found("Drawing not found")
        return web.json_response({"message": "Drawing deleted successfully"})

    @routes.patch("/api/v1/map/drawings/{drawing_id}")
    async def update_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        drawing_id = request.match_info.get("drawing_id")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        name = data.get("name")
        drawing_data = data.get("data")
        updated = app.database.map_drawings.update_drawing(
            drawing_id,
            identity_hash,
            name,
            drawing_data,
        )
        if not updated:
            return http_not_found("Drawing not found")
        return web.json_response({"message": "Drawing updated successfully"})

