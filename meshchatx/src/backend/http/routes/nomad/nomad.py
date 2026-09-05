# SPDX-License-Identifier: 0BSD
"""HTTP routes: nomad/nomad."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.nomad._names import *  # noqa: F403


def register_nomad_nomad_routes(routes: Any, app: Any) -> None:

    # identify self on existing nomadnetwork link

    @routes.post("/api/v1/nomadnetwork/{destination_hash}/identify")
    async def nomadnetwork_identify(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # convert destination hash to bytes
        destination_hash = bytes.fromhex(destination_hash)

        # identify to existing active link
        link = get_cached_active_link(destination_hash)
        if link is not None:
            link.identify(app.identity)
            return web.json_response(
                {
                    "message": "Identity has been sent!",
                },
            )

        # failed to identify
        return web.json_response(
            {
                "message": "Failed to identify. No active link to destination.",
            },
            status=500,
        )
