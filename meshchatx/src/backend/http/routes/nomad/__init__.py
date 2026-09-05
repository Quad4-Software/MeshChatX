# SPDX-License-Identifier: 0BSD
"""HTTP routes: nomad (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.nomad.nomad import (
    register_nomad_nomad_routes,
)


def register_nomad_routes(routes: Any, app: Any) -> None:
    register_nomad_nomad_routes(routes, app)
