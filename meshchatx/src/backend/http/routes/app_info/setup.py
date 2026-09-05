# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info setup."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.app_info._names import *  # noqa: F403, F405


def register_app_info_setup_routes(routes, app):

    @routes.post("/api/v1/setup/storage-migration")
    async def setup_storage_migration(request):
        if not app.migration_context.get("show_choice"):
            return web.json_response(
                {"error": "No storage migration is pending"},
                status=400,
            )
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        action = data.get("action")
        leg = app.migration_context["legacy_path"]
        tgt = app.migration_context["target_path"]
        try:
            assert_migration_context_paths(app.migration_context, leg, tgt)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        try:
            if action == "migrate":
                migrate_legacy_to_target(leg, tgt)
            elif action == "fresh":
                fresh_storage_at_target(tgt)
            else:
                return web.json_response({"error": "Unknown action"}, status=400)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=409)
        except OSError as e:
            return web.json_response({"error": str(e)}, status=500)
        return web.json_response({"ok": True, "restart_required": True})

    # acknowledge and reset integrity issues
