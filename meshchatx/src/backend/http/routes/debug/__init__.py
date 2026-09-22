# SPDX-License-Identifier: 0BSD
"""HTTP routes: debug (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.debug.debug import (
    register_debug_debug_routes,
)


def register_debug_routes(routes: Any, app: Any) -> None:
    register_debug_debug_routes(routes, app)
