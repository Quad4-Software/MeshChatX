# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites layout."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.favourites._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_body_limited,
)


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
        from meshchatx.src.backend.favourites_layout import (
            MAX_LAYOUT_JSON_BYTES,
            layout_payload_too_large,
        )

        content_length = request.content_length
        if content_length is not None and layout_payload_too_large(
            content_length,
        ):
            return http_payload_too_large("favourites layout exceeds size limit")
        try:
            raw = await read_body_limited(request, MAX_LAYOUT_JSON_BYTES + 1)
        except PayloadTooLargeError:
            return http_payload_too_large("favourites layout exceeds size limit")
        except Exception:
            return http_bad_request("Invalid request body")
        if layout_payload_too_large(len(raw)):
            return http_payload_too_large("favourites layout exceeds size limit")
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return http_bad_request("Invalid JSON body")
        layout = data.get("layout") if isinstance(data, dict) else None
        try:
            saved = app.database.announces.set_favourites_layout(layout)
        except ValueError as e:
            return http_bad_request(str(e))
        return web.json_response({"layout": saved})
