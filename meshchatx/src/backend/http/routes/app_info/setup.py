# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info setup."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_conflict,
    http_error_from_exception,
    http_payload_too_large,
)

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.app_info._names import *  # noqa: F403
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_app_info_setup_routes(routes, app):

    @routes.post("/api/v1/setup/storage-migration")
    async def setup_storage_migration(request):
        if not app.migration_context.get("show_choice"):
            return http_bad_request("No storage migration is pending")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid JSON")
        action = data.get("action")
        leg = app.migration_context["legacy_path"]
        tgt = app.migration_context["target_path"]
        try:
            assert_migration_context_paths(app.migration_context, leg, tgt)
        except ValueError as e:
            return http_bad_request(str(e))
        try:
            if action == "migrate":
                migrate_legacy_to_target(leg, tgt)
            elif action == "fresh":
                fresh_storage_at_target(tgt)
            else:
                return http_bad_request("Unknown action")
        except ValueError as e:
            return http_conflict(str(e))
        except OSError as e:
            return http_error_from_exception(e, fallback_status=500)
        return web.json_response({"ok": True, "restart_required": True})

    # acknowledge and reset integrity issues
