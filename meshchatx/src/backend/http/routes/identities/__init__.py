# SPDX-License-Identifier: 0BSD
"""HTTP routes: identities (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.identities.list import (
    register_identities_list_routes,
)
from meshchatx.src.backend.http.routes.identities.active import (
    register_identities_active_routes,
)


def register_identities_routes(routes: Any, app: Any) -> None:
    register_identities_list_routes(routes, app)
    register_identities_active_routes(routes, app)
