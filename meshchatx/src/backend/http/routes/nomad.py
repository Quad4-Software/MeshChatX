# SPDX-License-Identifier: 0BSD
"""HTTP routes: nomad."""

from __future__ import annotations

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_unexpected,
)
from meshchatx.src.backend.nomadnet_downloader import get_cached_active_link


def register_nomad_routes(routes, app):

    # identify self on existing nomadnetwork link
    @routes.post(API_V1_PREFIX + "/nomadnetwork/{destination_hash}/identify")
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
        return http_unexpected("Failed to identify. No active link to destination.")

    # delete lxmf message
