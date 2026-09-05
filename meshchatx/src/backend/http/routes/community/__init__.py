# SPDX-License-Identifier: 0BSD
"""HTTP routes: community (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.community.community import (
    register_community_community_routes,
)


def register_community_routes(routes: Any, app: Any) -> None:
    register_community_community_routes(routes, app)
