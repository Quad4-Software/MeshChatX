# SPDX-License-Identifier: 0BSD
"""Shared helpers for filesync HTTP routes."""

from __future__ import annotations

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.filesync._names import *  # noqa: F403, F405


def make_filesync_helpers(app):
    def _filesync_require_handler():
        return app._require_rns_tool_handler(
            app.rns_filesync_handler,
            "RNS FileSync",
        )

    return (_filesync_require_handler,)
