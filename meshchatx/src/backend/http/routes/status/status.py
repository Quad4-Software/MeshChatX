# SPDX-License-Identifier: 0BSD
"""HTTP routes: status/status."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.status._names import *  # noqa: F403


def register_status_status_routes(routes: Any, app: Any) -> None:

    @routes.get("/api/v1/status")
    async def status(request):
        return web.json_response(app._startup_status_payload())

    @routes.post("/api/v1/reticulum/recover")
    async def reticulum_recover(request):
        """Disable risky interfaces and retry network setup without wiping data."""
        if app._network_ready and app.current_context and app.current_context.running:
            return web.json_response(
                {
                    "message": "Network stack is already running",
                    "status": app._startup_status_payload(),
                },
            )

        identity = app._pending_identity or app.identity
        if identity is None:
            return web.json_response(
                {"message": "No identity available for recovery"},
                status=400,
            )

        config_path = app._reticulum_config_file_path()
        actions: list[str] = []
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}

        disable_all = bool(data.get("disable_all_interfaces"))
        named = data.get("disable_interfaces")
        if isinstance(named, list) and named:
            from meshchatx.src.backend.rns_startup_recovery import (
                disable_named_interfaces_in_config,
            )

            disabled = disable_named_interfaces_in_config(
                config_path,
                [str(n) for n in named],
            )
            actions.extend(disabled)
        elif disable_all:
            from meshchatx.src.backend.rns_startup_recovery import (
                disable_named_interfaces_in_config,
                list_enabled_interface_names,
            )

            names = list_enabled_interface_names(config_path)
            disabled = disable_named_interfaces_in_config(config_path, names)
            actions.extend(disabled)
        else:
            from meshchatx.src.backend.rns_startup_recovery import (
                apply_startup_recovery_step,
            )

            for attempt in range(4):
                disabled = apply_startup_recovery_step(
                    config_path,
                    app._startup_error or "manual recover",
                    attempt=attempt,
                )
                actions.extend(disabled)
                if disabled:
                    break

        app._rns_recovery_actions = actions
        app._startup_error = None
        app._startup_stage = "starting"
        app._network_degraded = False
        app._ui_ready = True
        app._network_ready = False
        app._reticulum_secondary_started = False
        if hasattr(app, "reticulum"):
            with contextlib.suppress(Exception):
                delattr(app, "reticulum")

        try:
            app.setup_identity(identity)
            app._mark_network_ready()
            app._finish_deferred_startup_services()
            return web.json_response(
                {
                    "message": "Network stack recovered",
                    "disabled_interfaces": actions,
                    "status": app._startup_status_payload(),
                },
            )
        except Exception as exc:
            traceback.print_exc()
            app._mark_network_degraded(str(exc))
            return web.json_response(
                {
                    "message": "Recovery attempt failed",
                    "error": str(exc),
                    "disabled_interfaces": actions,
                    "status": app._startup_status_payload(),
                },
                status=500,
            )

    @routes.get("/api/v1/self-test")
    async def self_test(request):
        results = app.run_self_test()
        return web.json_response(results)
