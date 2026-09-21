# SPDX-License-Identifier: 0BSD
"""HTTP routes: database/health."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.errors import (
    http_error_from_exception,
    http_payload_too_large,
)

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.routes.database._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_database_health_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/database/health")
    async def database_health(request):
        try:
            return web.json_response(
                {
                    "database": app.database.get_database_health_snapshot(),
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/database/vacuum")
    async def database_vacuum(request):
        try:
            result = app.database.run_database_vacuum()
            return web.json_response(
                {
                    "message": "Database vacuum completed",
                    "database": result,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/database/recover")
    async def database_recover(request):
        try:
            result = app.database.run_database_recovery()
            return web.json_response(
                {
                    "message": "Database recovery routine completed",
                    "database": result,
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/database/auto-recover")
    async def database_auto_recover(request):
        try:
            try:
                data = await read_json_limited(request)
            except PayloadTooLargeError:
                return http_payload_too_large(
                    "Upload exceeds size limit",
                    strategy="none",
                )
            except Exception:
                data = {}
            if not isinstance(data, dict):
                data = {}
            relaunch = bool(data.get("relaunch", True))
            result = app.auto_recover_database(relaunch=relaunch)
            status = 200 if result.get("strategy") != "none" else 500
            return web.json_response(
                {
                    "message": result.get("message"),
                    "strategy": result.get("strategy"),
                    "requires_relaunch": bool(result.get("requires_relaunch")),
                    "backup": result.get("backup"),
                    "database": result.get("database"),
                    "restore_result": result.get("restore_result"),
                    "error": result.get("error"),
                },
                status=status,
            )
        except Exception as e:
            return http_error_from_exception(
                e,
                key="message",
                extra={"strategy": "none"},
                fallback_status=500,
            )
