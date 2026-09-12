# SPDX-License-Identifier: 0BSD
"""HTTP routes: sideband."""

from __future__ import annotations

import asyncio

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_error_from_exception,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_sideband_routes(routes, app):

    @routes.get(API_V1_PREFIX + "/sideband-plugins/config")
    async def sideband_plugins_config_get(request):
        return web.json_response(app.sideband_plugin_loader.get_config())

    @routes.post(API_V1_PREFIX + "/sideband-plugins/config")
    async def sideband_plugins_config_set(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
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
            return http_error_from_exception(e, key="message")

    @routes.get(API_V1_PREFIX + "/sideband-plugins")
    async def sideband_plugins_list(request):
        return web.json_response(
            {
                "config": app.sideband_plugin_loader.get_config(),
                "plugins": app.sideband_plugin_loader.list_plugins(),
            },
        )

    @routes.post(API_V1_PREFIX + "/sideband-plugins/reload")
    async def sideband_plugins_reload(request):
        try:
            result = await asyncio.to_thread(app.sideband_plugin_loader.reload)
            app._ensure_sideband_telemetry_loop()
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, key="message")
