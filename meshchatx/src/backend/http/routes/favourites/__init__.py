# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.favourites.announces import (
    register_favourites_announces_routes,
)
from meshchatx.src.backend.http.routes.favourites.favourites_crud import (
    register_favourites_favourites_crud_routes,
)
from meshchatx.src.backend.http.routes.favourites.layout import (
    register_favourites_layout_routes,
)


def register_favourites_routes(routes: Any, app: Any) -> None:
    register_favourites_announces_routes(routes, app)
    register_favourites_favourites_crud_routes(routes, app)
    register_favourites_layout_routes(routes, app)
