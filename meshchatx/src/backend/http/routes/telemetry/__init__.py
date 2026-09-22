# SPDX-License-Identifier: 0BSD
"""HTTP routes: telemetry (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.telemetry.telemetry import (
    register_telemetry_telemetry_routes,
)


def register_telemetry_routes(routes: Any, app: Any) -> None:
    register_telemetry_telemetry_routes(routes, app)
