# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance transport."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.reticulum_instance._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_conflict,
    http_unexpected,
)


def register_reticulum_instance_transport_routes(routes, app):

    def _transport_is_active():
        """True only when Reticulum reports transport running on this instance."""
        reticulum = getattr(app, "reticulum", None)
        if reticulum is None:
            return False
        try:
            return reticulum.transport_enabled() is True
        except Exception:
            return False

    def _is_shared_instance_client():
        """True when this process attached to another shared RNS instance.

        RNS forces transport off on shared-instance clients (the shared
        instance runs transport), so the local enable_transport flag cannot
        take effect until this process owns the stack.
        """
        reticulum = getattr(app, "reticulum", None)
        return getattr(reticulum, "is_connected_to_shared_instance", False) is True

    # enable transport mode
    @routes.post("/api/v1/reticulum/enable-transport")
    async def reticulum_enable_transport(request):
        # enable transport mode
        reticulum_config = app._get_reticulum_section()
        reticulum_config["enable_transport"] = True
        if not app._write_reticulum_config():
            return http_unexpected("Failed to write Reticulum config")

        try:
            reloaded = await app.reload_reticulum()
        except Exception as e:
            logger.debug(f"Failed to reload RNS after enabling transport: {e}")
            reloaded = False

        if not reloaded:
            if _is_shared_instance_client():
                return http_unexpected(
                    "Transport mode was saved to the Reticulum config, but the "
                    "RNS reload failed and this process is attached to a "
                    "shared Reticulum instance. Stop the other Reticulum "
                    "program using this config, then restart MeshChatX.",
                    transport_enabled=False,
                    is_connected_to_shared_instance=True,
                )
            return http_unexpected(
                "Transport mode was enabled in config, but RNS reload failed.",
                transport_enabled=False,
            )

        if not _transport_is_active():
            if _is_shared_instance_client():
                return http_conflict(
                    "Transport mode was saved to the Reticulum config, but "
                    "this process is attached to a shared Reticulum instance "
                    "that controls transport. Enable transport on that "
                    "instance, or stop it and restart MeshChatX.",
                    code="transport_managed_by_shared_instance",
                    transport_enabled=False,
                    is_connected_to_shared_instance=True,
                )
            return http_unexpected(
                "Transport mode was enabled in config and RNS restarted, but "
                "transport is not active on this instance.",
                transport_enabled=False,
            )

        return web.json_response(
            {
                "message": "Transport mode enabled and RNS restarted successfully.",
                "transport_enabled": True,
            },
        )

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
            return http_unexpected("Failed to write Reticulum config")

        try:
            reloaded = await app.reload_reticulum()
        except Exception as e:
            logger.debug(f"Failed to reload RNS after disabling transport: {e}")
            reloaded = False

        if not reloaded:
            return http_unexpected(
                "Transport mode was disabled in config, but RNS reload failed.",
            )

        if _transport_is_active():
            return http_unexpected(
                "Transport mode was disabled in config and RNS restarted, but "
                "transport is still active on this instance.",
                transport_enabled=True,
            )

        return web.json_response(
            {
                "message": "Transport mode disabled and RNS restarted successfully.",
                "transport_enabled": False,
            },
        )
