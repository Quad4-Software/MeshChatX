# SPDX-License-Identifier: 0BSD
"""HTTP routes: page_nodes (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.page_nodes.page_nodes import (
    register_page_nodes_page_nodes_routes,
)


def register_page_nodes_routes(routes: Any, app: Any) -> None:
    register_page_nodes_page_nodes_routes(routes, app)
