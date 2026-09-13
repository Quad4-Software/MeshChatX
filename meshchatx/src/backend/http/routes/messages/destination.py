# SPDX-License-Identifier: 0BSD
"""HTTP routes: messages/destination."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.messages._names import *  # noqa: F403
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)



def register_messages_destination_routes(routes: Any, app: Any) -> None:

    # get custom destination display name

    @routes.get("/api/v1/destination/{destination_hash}/custom-display-name")
    async def destination_custom_display_name_get(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        return web.json_response(
            {
                "custom_display_name": app.get_custom_destination_display_name(
                    destination_hash,
                ),
            },
        )

    @routes.post(
        "/api/v1/destination/{destination_hash}/custom-display-name/update",
    )
    async def destination_custom_display_name_update(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # get request data
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        raw_name = data.get("display_name")
        if raw_name is None:
            display_name = ""
        elif isinstance(raw_name, str):
            display_name = raw_name.strip()
        else:
            display_name = str(raw_name).strip()

        # update display name if provided
        if len(display_name) > 0:
            app.database.announces.upsert_custom_display_name(
                destination_hash,
                display_name,
            )
            return web.json_response(
                {
                    "message": "Custom display name has been updated",
                },
            )

        # otherwise remove display name
        app.database.announces.delete_custom_display_name(destination_hash)
        return web.json_response(
            {
                "message": "Custom display name has been removed",
            },
        )

    @routes.get("/api/v1/destination/{destination_hash}/lxmf-stamp-info")
    async def destination_lxmf_stamp_info(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # convert destination hash to bytes
        try:
            destination_hash_bytes = bytes.fromhex(destination_hash)
        except (TypeError, ValueError):
            return http_bad_request("invalid destination_hash")

        # get lxmf stamp cost from announce in database
        lxmf_stamp_cost = None
        announce = app.database.announces.get_announce_by_hash(destination_hash)
        if announce is not None:
            lxmf_stamp_cost = parse_lxmf_stamp_cost(
                announce["app_data"],
            )

        # get outbound ticket expiry for this lxmf destination
        lxmf_outbound_ticket_expiry = app.message_router.get_outbound_ticket_expiry(
            destination_hash_bytes,
        )
        if lxmf_outbound_ticket_expiry is not None and not isinstance(
            lxmf_outbound_ticket_expiry,
            (int, float),
        ):
            lxmf_outbound_ticket_expiry = None

        return web.json_response(
            {
                "lxmf_stamp_info": {
                    "stamp_cost": lxmf_stamp_cost,
                    "outbound_ticket_expiry": lxmf_outbound_ticket_expiry,
                },
            },
        )

    @routes.get("/api/v1/destination/{destination_hash}/delivery-diagnostics")
    async def destination_delivery_diagnostics(request):
        destination_hash = request.match_info.get("destination_hash", "")
        if not destination_hash:
            return http_bad_request("destination_hash is required")
        return web.json_response(
            build_delivery_diagnostics(app, destination_hash),
        )

