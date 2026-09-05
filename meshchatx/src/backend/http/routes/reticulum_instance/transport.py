# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance transport."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.reticulum_instance._names import *  # noqa: F403, F405


def register_reticulum_instance_transport_routes(routes, app):

    # enable transport mode
    @routes.post("/api/v1/reticulum/enable-transport")
    async def reticulum_enable_transport(request):
        # enable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = True
        if not app._write_reticulum_config():
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        if not await app.reload_reticulum():
            return web.json_response(
                {
                    "message": "Transport mode was enabled in config, but RNS reload failed.",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Transport mode enabled and RNS restarted successfully.",
            },
        )

    # disable transport mode

    # disable transport mode
    @routes.post("/api/v1/reticulum/disable-transport")
    async def reticulum_disable_transport(request):
        # disable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = False
        i2p_support.disable_i2p_when_transport_off(
            app._get_interfaces_section(),
            reticulum_config,
        )
        if not app._write_reticulum_config():
            return web.json_response(
                {
                    "message": "Failed to write Reticulum config",
                },
                status=500,
            )

        if not await app.reload_reticulum():
            return web.json_response(
                {
                    "message": "Transport mode was disabled in config, but RNS reload failed.",
                },
                status=500,
            )

        return web.json_response(
            {
                "message": "Transport mode disabled and RNS restarted successfully.",
            },
        )
