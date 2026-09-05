# SPDX-License-Identifier: 0BSD

"""Shared helpers for rrc HTTP routes."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rrc._names import *  # noqa: F403, F405


RRC_ROOM_MESSAGES_DEFAULT_LIMIT = 200
RRC_ROOM_MESSAGES_MAX_LIMIT = 1000


def make_rrc_helpers(app):
    def _rrc_require_manager():
        manager = app.rrc_manager
        if manager is None:
            return None, web.json_response(
                {"message": "Relay chat is not available"},
                status=503,
            )
        return manager, None

    def _rrc_require_hub(hub_hash_hex):
        manager, error = _rrc_require_manager()
        if error is not None:
            return None, None, error
        hub = manager.find_hub_by_hex(hub_hash_hex)
        if hub is None:
            return (
                manager,
                None,
                web.json_response(
                    {"message": "Hub not found"},
                    status=404,
                ),
            )
        return manager, hub, None

    def _rrc_server_require_manager():
        manager = app.rrc_server_manager
        if manager is None:
            return None, web.json_response(
                {"message": "Relay chat hosting is not available"},
                status=503,
            )
        return manager, None

    def _rrc_server_require_hub(hub_id):
        manager, error = _rrc_server_require_manager()
        if error is not None:
            return None, None, error
        hub = manager.find_hub(hub_id)
        if hub is None:
            return (
                manager,
                None,
                web.json_response(
                    {"message": "Hub not found"},
                    status=404,
                ),
            )
        return manager, hub, None

    # Reticulum Relay Chat hosting (local hubs)

    return (
        _rrc_require_manager,
        _rrc_require_hub,
        _rrc_server_require_manager,
        _rrc_server_require_hub,
    )
