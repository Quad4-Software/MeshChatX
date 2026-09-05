# SPDX-License-Identifier: 0BSD
"""HTTP routes: maintenance (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.maintenance.ops import (
    register_maintenance_ops_routes,
)


def register_maintenance_routes(routes: Any, app: Any) -> None:
    register_maintenance_ops_routes(routes, app)
