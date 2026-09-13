# SPDX-License-Identifier: 0BSD
"""HTTP routes: map (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.map.tiles import register_map_tiles_routes
from meshchatx.src.backend.http.routes.map.drawings import register_map_drawings_routes
from meshchatx.src.backend.http.routes.map.overlays import register_map_overlays_routes
from meshchatx.src.backend.http.routes.map.export import register_map_export_routes
from meshchatx.src.backend.http.routes.map.data import register_map_data_routes


def register_map_routes(routes: Any, app: Any) -> None:
    register_map_tiles_routes(routes, app)
    register_map_drawings_routes(routes, app)
    register_map_overlays_routes(routes, app)
    register_map_export_routes(routes, app)
    register_map_data_routes(routes, app)
