# SPDX-License-Identifier: 0BSD

"""Shared helpers for rn_tools HTTP routes."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403, F405


def make_rn_tools_helpers(app):
    def _rnsh_require_manager():
        manager = app.rnsh_manager
        if manager is None:
            return None, web.json_response(
                {"message": "RNSH manager is not available"},
                status=503,
            )
        return manager, None

    def _rnx_require_manager():
        manager = app.rnx_manager
        if manager is None:
            return None, web.json_response(
                {"message": "RNX manager is not available"},
                status=503,
            )
        return manager, None

    return (
        _rnsh_require_manager,
        _rnx_require_manager,
    )
