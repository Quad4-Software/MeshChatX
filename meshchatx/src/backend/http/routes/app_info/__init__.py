# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.app_info.info import (
    register_app_info_info_routes,
)
from meshchatx.src.backend.http.routes.app_info.seen import (
    register_app_info_seen_routes,
)
from meshchatx.src.backend.http.routes.app_info.setup import (
    register_app_info_setup_routes,
)
from meshchatx.src.backend.http.routes.app_info.shutdown import (
    register_app_info_shutdown_routes,
)


def register_app_info_routes(routes: Any, app: Any) -> None:
    register_app_info_info_routes(routes, app)
    register_app_info_seen_routes(routes, app)
    register_app_info_setup_routes(routes, app)
    register_app_info_shutdown_routes(routes, app)
