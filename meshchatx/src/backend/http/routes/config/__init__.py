# SPDX-License-Identifier: 0BSD
"""HTTP routes: config (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.config.config import (
    register_config_config_routes,
)


def register_config_routes(routes: Any, app: Any) -> None:
    register_config_config_routes(routes, app)
