# SPDX-License-Identifier: 0BSD

"""Shared helpers for rn_tools HTTP routes."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import http_unavailable
from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403


def make_rn_tools_helpers(app):
    def _rnsh_require_manager():
        manager = app.rnsh_manager
        if manager is None:
            return None, http_unavailable("RNSH manager is not available")
        return manager, None

    def _rnx_require_manager():
        manager = app.rnx_manager
        if manager is None:
            return None, http_unavailable("RNX manager is not available")
        return manager, None

    return (
        _rnsh_require_manager,
        _rnx_require_manager,
    )
