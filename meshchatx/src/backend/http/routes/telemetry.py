# SPDX-License-Identifier: 0BSD
"""HTTP routes: telemetry."""

from __future__ import annotations

import json

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.telemetry_utils import Telemeter


def register_telemetry_routes(routes, app):

    # get latest telemetry for all peers
    @routes.get(API_V1_PREFIX + "/telemetry/peers")
    async def get_all_latest_telemetry(request):
        results = app.database.telemetry.get_all_latest_telemetry()
        telemetry_list = []
        for r in results:
            unpacked = Telemeter.from_packed(r["data"])
            telemetry_list.append(
                {
                    "destination_hash": r["destination_hash"],
                    "timestamp": r["timestamp"],
                    "telemetry": unpacked,
                    "physical_link": json.loads(r["physical_link"])
                    if r["physical_link"]
                    else None,
                    "updated_at": r["updated_at"],
                    "is_tracking": app.database.telemetry.is_tracking(
                        r["destination_hash"],
                    ),
                },
            )
        return web.json_response({"telemetry": telemetry_list})

    @routes.get(API_V1_PREFIX + "/telemetry/trusted-peers")
    async def telemetry_trusted_peers_get(request):
        # get all contacts that are telemetry trusted
        contacts = app.database.provider.fetchall(
            "SELECT * FROM contacts WHERE is_telemetry_trusted = 1 ORDER BY name ASC",
        )
        return web.json_response({"trusted_peers": [dict(c) for c in contacts]})

    # toggle telemetry tracking for a destination

    # toggle telemetry tracking for a destination
    @routes.post(API_V1_PREFIX + "/telemetry/tracking/{destination_hash}/toggle")
    async def toggle_telemetry_tracking(request):
        destination_hash = request.match_info["destination_hash"]
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        is_tracking = data.get("is_tracking")

        new_status = app.database.telemetry.toggle_tracking(
            destination_hash,
            is_tracking,
        )
        return web.json_response({"status": "ok", "is_tracking": new_status})

    # get all tracked peers

    # get all tracked peers
    @routes.get(API_V1_PREFIX + "/telemetry/tracking")
    async def get_tracked_peers(request):
        results = app.database.telemetry.get_tracked_peers()
        return web.json_response({"tracked_peers": results})

    # get telemetry history for a destination

    # get telemetry history for a destination
    @routes.get(API_V1_PREFIX + "/telemetry/history/{destination_hash}")
    async def get_telemetry_history(request):
        destination_hash = request.match_info.get("destination_hash")
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))

        results = app.database.telemetry.get_telemetry_history(
            destination_hash,
            limit,
            offset,
        )
        telemetry_list = []
        for r in results:
            unpacked = Telemeter.from_packed(r["data"])
            telemetry_list.append(
                {
                    "destination_hash": r["destination_hash"],
                    "timestamp": r["timestamp"],
                    "telemetry": unpacked,
                    "physical_link": json.loads(r["physical_link"])
                    if r["physical_link"]
                    else None,
                    "updated_at": r["updated_at"],
                },
            )
        return web.json_response({"telemetry": telemetry_list})

    # get latest telemetry for a destination

    # get latest telemetry for a destination
    @routes.get(API_V1_PREFIX + "/telemetry/latest/{destination_hash}")
    async def get_latest_telemetry(request):
        destination_hash = request.match_info.get("destination_hash")
        r = app.database.telemetry.get_latest_telemetry(destination_hash)
        if not r:
            return http_not_found("No telemetry found")

        unpacked = Telemeter.from_packed(r["data"])
        return web.json_response(
            {
                "destination_hash": r["destination_hash"],
                "timestamp": r["timestamp"],
                "telemetry": unpacked,
                "physical_link": json.loads(r["physical_link"])
                if r["physical_link"]
                else None,
                "updated_at": r["updated_at"],
            },
        )

    # upload offline map
