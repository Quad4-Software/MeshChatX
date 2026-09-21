# SPDX-License-Identifier: 0BSD
"""HTTP routes: blocklist/blocklist."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_payload_too_large,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.blocklist._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_blocklist_blocklist_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/blocked-destinations")
    async def blocked_destinations_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            blocked = app.database.misc.get_blocked_destinations()
            blocked_list = [
                {
                    "destination_hash": b["destination_hash"],
                    "created_at": b["created_at"],
                }
                for b in blocked
            ]
            return web.json_response(
                {
                    "blocked_destinations": blocked_list,
                },
            )
        except Exception as e:
            logger.exception("blocked_destinations_get failed")
            return http_for_database_exception(e)

    @routes.post("/api/v1/blocked-destinations")
    async def blocked_destinations_add(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = data.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return http_bad_request("Invalid destination hash")

        try:
            app.banish_lxmf_peer(destination_hash)
        except Exception:
            return http_bad_request("Failed to banish destination")

        return web.json_response({"message": "ok"})

    @routes.delete("/api/v1/blocked-destinations/{destination_hash}")
    async def blocked_destinations_delete(request):
        destination_hash = request.match_info.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return http_bad_request("Invalid destination hash")

        try:
            app.lift_lxmf_peer_banishment(destination_hash)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)
