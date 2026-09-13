# SPDX-License-Identifier: 0BSD
"""HTTP routes: auth (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.auth.csrf import (
    register_auth_csrf_routes,
)
from meshchatx.src.backend.http.routes.auth.security import (
    register_auth_security_routes,
)
from meshchatx.src.backend.http.routes.auth.session import (
    register_auth_session_routes,
)


def register_auth_routes(routes: Any, app: Any) -> None:
    register_auth_security_routes(routes, app)
    register_auth_csrf_routes(routes, app)
    register_auth_session_routes(routes, app)
