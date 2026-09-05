# SPDX-License-Identifier: 0BSD
"""HTTP routes: rrc (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.rrc.hubs import register_rrc_hubs_routes
from meshchatx.src.backend.http.routes.rrc.servers import register_rrc_servers_routes


def register_rrc_routes(routes: Any, app: Any) -> None:
    register_rrc_hubs_routes(routes, app)
    register_rrc_servers_routes(routes, app)
