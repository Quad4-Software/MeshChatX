# SPDX-License-Identifier: 0BSD
"""HTTP routes: plugins (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.plugins.plugins import (
    register_plugins_plugins_routes,
)


def register_plugins_routes(routes: Any, app: Any) -> None:
    register_plugins_plugins_routes(routes, app)
