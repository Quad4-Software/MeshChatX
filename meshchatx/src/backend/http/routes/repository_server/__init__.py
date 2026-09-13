# SPDX-License-Identifier: 0BSD
"""HTTP routes: repository_server (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.repository_server.repo import (
    register_repository_server_repo_routes,
)


def register_repository_server_routes(routes: Any, app: Any) -> None:
    register_repository_server_repo_routes(routes, app)
