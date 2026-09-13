# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info seen."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.app_info._names import *  # noqa: F403, F405

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_app_info_seen_routes(routes, app):

    # mark tutorial as seen
    @routes.post("/api/v1/app/tutorial/seen")
    async def app_tutorial_seen(request):
        app.config.set("tutorial_seen", True)
        return web.json_response({"message": "Tutorial marked as seen"})

    # acknowledge and reset integrity issues
    @routes.post("/api/v1/app/integrity/acknowledge")
    async def app_integrity_acknowledge(request):
        manager = getattr(app.current_context, "integrity_manager", None)
        if manager:
            manager.save_manifest(reason="acknowledge")
        app.integrity_issues = []
        return web.json_response(
            {"message": "Integrity issues acknowledged and manifest reset"},
        )

    # mark changelog as seen

    # mark changelog as seen
    @routes.post("/api/v1/app/changelog/seen")
    async def app_changelog_seen(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        version = data.get("version")
        if not version:
            return http_bad_request("Version required")

        app.config.set("changelog_seen_version", version)
        return web.json_response(
            {"message": f"Changelog version {version} marked as seen"},
        )

    @routes.post("/api/v1/app/channel-prompt/seen")
    async def app_channel_prompt_seen(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid JSON")
        key = data.get("key") if isinstance(data, dict) else None
        if not key or not isinstance(key, str) or not key.strip():
            return http_bad_request("key required")
        seen_key = key.strip()
        if len(seen_key) > 200:
            return http_bad_request("key too long")
        app.config.set("channel_prompt_seen", seen_key)
        return web.json_response({"message": "Channel prompt marked as seen"})

    # shutdown app
