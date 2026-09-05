# SPDX-License-Identifier: 0BSD
"""HTTP routes: auth CSRF."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.auth._names import *  # noqa: F403


def register_auth_csrf_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/auth/csrf")
    async def auth_csrf(request):
        try:
            session = await get_session(request)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
        token = ensure_session_csrf_token(session)
        return web.json_response({"csrf_token": token})
