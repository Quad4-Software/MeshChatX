# SPDX-License-Identifier: 0BSD
"""HTTP routes: community/community."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.community._names import *  # noqa: F403


def register_community_community_routes(routes: Any, app: Any) -> None:

    # fetch community interfaces

    @routes.get("/api/v1/community-interfaces")
    async def community_interfaces(request):
        interfaces = await app.community_interfaces_manager.get_interfaces()
        return web.json_response({"interfaces": interfaces})
