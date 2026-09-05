# SPDX-License-Identifier: 0BSD
"""HTTP routes: blocklist/blocklist."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.blocklist._names import *  # noqa: F403


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
        data = await request.json()
        destination_hash = data.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return web.json_response(
                {"error": "Invalid destination hash"},
                status=400,
            )

        try:
            app.banish_lxmf_peer(destination_hash)
        except Exception:
            return web.json_response(
                {"error": "Failed to banish destination"},
                status=400,
            )

        return web.json_response({"message": "ok"})

    @routes.delete("/api/v1/blocked-destinations/{destination_hash}")
    async def blocked_destinations_delete(request):
        destination_hash = request.match_info.get("destination_hash", "")
        if not destination_hash or len(destination_hash) != 32:
            return web.json_response(
                {"error": "Invalid destination hash"},
                status=400,
            )

        try:
            app.lift_lxmf_peer_banishment(destination_hash)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
