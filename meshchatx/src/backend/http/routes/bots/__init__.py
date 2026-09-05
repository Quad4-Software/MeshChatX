# SPDX-License-Identifier: 0BSD
"""HTTP routes: bots (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.bots.bots import (
    register_bots_bots_routes,
)


def register_bots_routes(routes: Any, app: Any) -> None:
    register_bots_bots_routes(routes, app)
