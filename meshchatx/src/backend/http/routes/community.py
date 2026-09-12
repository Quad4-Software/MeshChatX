# SPDX-License-Identifier: 0BSD
"""HTTP routes: community."""

from __future__ import annotations

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX


def register_community_routes(routes, app):

    # fetch community interfaces
    @routes.get(API_V1_PREFIX + "/community-interfaces")
    async def community_interfaces(request):
        interfaces = await app.community_interfaces_manager.get_interfaces()
        return web.json_response({"interfaces": interfaces})

    # enable reticulum interface
