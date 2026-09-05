# SPDX-License-Identifier: 0BSD
"""HTTP routes: gifs (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.gifs.gifs import (
    register_gifs_gifs_routes,
)


def register_gifs_routes(routes: Any, app: Any) -> None:
    register_gifs_gifs_routes(routes, app)
