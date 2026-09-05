# SPDX-License-Identifier: 0BSD
"""HTTP routes: shell (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.shell.static import (
    register_shell_static_routes,
)


def register_shell_routes(routes: Any, app: Any) -> None:
    register_shell_static_routes(routes, app)
