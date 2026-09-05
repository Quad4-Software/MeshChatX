# SPDX-License-Identifier: 0BSD
"""HTTP routes: websocket_upgrade (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.websocket_upgrade.upgrade import (
    register_websocket_upgrade_upgrade_routes,
)


def register_websocket_upgrade_routes(routes: Any, app: Any) -> None:
    register_websocket_upgrade_upgrade_routes(routes, app)
