# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info seen."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.app_info._names import *  # noqa: F403, F405


def register_app_info_seen_routes(routes, app):

    # mark tutorial as seen
    @routes.post("/api/v1/app/tutorial/seen")
    async def app_tutorial_seen(request):
        app.config.set("tutorial_seen", True)
        return web.json_response({"message": "Tutorial marked as seen"})

    # acknowledge and reset integrity issues
    @routes.post("/api/v1/app/integrity/acknowledge")
    async def app_integrity_acknowledge(request):
        if app.current_context:
            app.current_context.integrity_manager.save_manifest()
        app.integrity_issues = []
        return web.json_response(
            {"message": "Integrity issues acknowledged and manifest reset"},
        )

    # mark changelog as seen

    # mark changelog as seen
    @routes.post("/api/v1/app/changelog/seen")
    async def app_changelog_seen(request):
        data = await request.json()
        version = data.get("version")
        if not version:
            return web.json_response({"error": "Version required"}, status=400)

        app.config.set("changelog_seen_version", version)
        return web.json_response(
            {"message": f"Changelog version {version} marked as seen"},
        )

    @routes.post("/api/v1/app/channel-prompt/seen")
    async def app_channel_prompt_seen(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        key = data.get("key") if isinstance(data, dict) else None
        if not key or not isinstance(key, str) or not key.strip():
            return web.json_response({"error": "key required"}, status=400)
        seen_key = key.strip()
        if len(seen_key) > 200:
            return web.json_response({"error": "key too long"}, status=400)
        app.config.set("channel_prompt_seen", seen_key)
        return web.json_response({"message": "Channel prompt marked as seen"})

    # shutdown app
