# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites layout."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.favourites._names import *  # noqa: F403


def register_favourites_layout_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/favourites/layout")
    async def favourites_layout_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            layout = app.database.announces.get_favourites_layout()
            return web.json_response({"layout": layout})
        except Exception as e:
            logger.exception("favourites_layout_get failed")
            return http_for_database_exception(e)

    @routes.put("/api/v1/favourites/layout")
    async def favourites_layout_put(request):
        from meshchatx.src.backend.favourites_layout import layout_payload_too_large

        content_length = request.content_length
        if content_length is not None and layout_payload_too_large(
            content_length,
        ):
            return web.json_response(
                {"message": "favourites layout exceeds size limit"},
                status=413,
            )
        try:
            raw = await request.read()
        except Exception:
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )
        if layout_payload_too_large(len(raw)):
            return web.json_response(
                {"message": "favourites layout exceeds size limit"},
                status=413,
            )
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return web.json_response(
                {"message": "Invalid JSON body"},
                status=400,
            )
        layout = data.get("layout") if isinstance(data, dict) else None
        try:
            saved = app.database.announces.set_favourites_layout(layout)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"layout": saved})
