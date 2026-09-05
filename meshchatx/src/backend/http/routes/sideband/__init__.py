# SPDX-License-Identifier: 0BSD
"""HTTP routes: sideband (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.sideband.sideband import (
    register_sideband_sideband_routes,
)


def register_sideband_routes(routes: Any, app: Any) -> None:
    register_sideband_sideband_routes(routes, app)
