# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync ACL."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *  # noqa: F403


def register_filesync_acl_routes(routes: Any, app: Any) -> None:
    (_filesync_require_handler,) = make_filesync_helpers(app)

    @routes.get("/api/v1/filesync/acl")
    async def filesync_acl_get(_request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        return web.json_response(app.rns_filesync_handler.get_acl())

    @routes.post("/api/v1/filesync/acl")
    async def filesync_acl_post(request):
        not_ready = _filesync_require_handler()
        if not_ready is not None:
            return not_ready
        data = await request.json()
        if not isinstance(data, dict):
            return web.json_response({"message": "Invalid JSON body"}, status=400)
        perms = data.get("perms")
        if perms is not None and not isinstance(perms, list):
            return web.json_response(
                {"message": "perms must be a list"},
                status=400,
            )
        try:
            result = await asyncio.to_thread(
                app.rns_filesync_handler.update_acl,
                identity_hash=data.get("identity_hash"),
                perms=perms,
                enforce=data.get("enforce"),
                rules_text=data.get("rules_text"),
                replace=bool(data.get("replace", False)),
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        if not result.get("ok"):
            return web.json_response(
                {"message": result.get("error", "acl update failed")},
                status=400,
            )
        return web.json_response(result)
