# SPDX-License-Identifier: 0BSD
"""HTTP routes: status (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.status.status import (
    register_status_status_routes,
)


def register_status_routes(routes: Any, app: Any) -> None:
    register_status_status_routes(routes, app)
