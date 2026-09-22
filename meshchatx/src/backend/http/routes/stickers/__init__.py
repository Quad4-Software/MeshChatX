# SPDX-License-Identifier: 0BSD
"""HTTP routes: stickers (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.stickers.import_export import (
    register_stickers_import_export_routes,
)
from meshchatx.src.backend.http.routes.stickers.items import (
    register_stickers_items_routes,
)
from meshchatx.src.backend.http.routes.stickers.packs import (
    register_stickers_packs_routes,
)


def register_stickers_routes(routes: Any, app: Any) -> None:
    register_stickers_items_routes(routes, app)
    register_stickers_import_export_routes(routes, app)
    register_stickers_packs_routes(routes, app)
