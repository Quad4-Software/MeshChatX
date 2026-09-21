# SPDX-License-Identifier: 0BSD
"""HTTP routes: filesync ACL."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_payload_too_large,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.filesync._helpers import make_filesync_helpers
from meshchatx.src.backend.http.routes.filesync._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


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
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        if not isinstance(data, dict):
            return http_bad_request("Invalid JSON body")
        perms = data.get("perms")
        if perms is not None and not isinstance(perms, list):
            return http_bad_request("perms must be a list")
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
            return http_error_from_exception(e, key="message", fallback_status=500)
        if not result.get("ok"):
            return http_bad_request(result.get("error", "acl update failed"))
        return web.json_response(result)
