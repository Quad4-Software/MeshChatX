# SPDX-License-Identifier: 0BSD
"""HTTP routes: database (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.database.snapshots import (
    register_database_snapshots_routes,
)
from meshchatx.src.backend.http.routes.database.backups import (
    register_database_backups_routes,
)
from meshchatx.src.backend.http.routes.database.health import (
    register_database_health_routes,
)


def register_database_routes(routes: Any, app: Any) -> None:
    register_database_snapshots_routes(routes, app)
    register_database_backups_routes(routes, app)
    register_database_health_routes(routes, app)
