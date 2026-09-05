# SPDX-License-Identifier: 0BSD
"""HTTP routes: sideband/sideband."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.sideband._names import *  # noqa: F403


def register_sideband_sideband_routes(routes: Any, app: Any) -> None:

    @routes.get("/api/v1/sideband-plugins/config")
    async def sideband_plugins_config_get(request):
        return web.json_response(app.sideband_plugin_loader.get_config())

    @routes.post("/api/v1/sideband-plugins/config")
    async def sideband_plugins_config_set(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        try:
            result = await asyncio.to_thread(
                app.sideband_plugin_loader.set_config,
                service_plugins_enabled=data.get("service_plugins_enabled"),
                command_plugins_enabled=data.get("command_plugins_enabled"),
                command_plugins_path=data.get("command_plugins_path"),
            )
            app._ensure_sideband_telemetry_loop()
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)

    @routes.get("/api/v1/sideband-plugins")
    async def sideband_plugins_list(request):
        return web.json_response(
            {
                "config": app.sideband_plugin_loader.get_config(),
                "plugins": app.sideband_plugin_loader.list_plugins(),
            },
        )

    @routes.post("/api/v1/sideband-plugins/reload")
    async def sideband_plugins_reload(request):
        try:
            result = await asyncio.to_thread(app.sideband_plugin_loader.reload)
            app._ensure_sideband_telemetry_loop()
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
