# SPDX-License-Identifier: 0BSD
"""Shared helpers for archives HTTP routes."""

from __future__ import annotations

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.archives._names import *  # noqa: F403, F405


def resolve_node_name(app, destination_hash: str) -> str:
    node_name = app.get_custom_destination_display_name(destination_hash)
    if not node_name:
        db_announce = app.database.announces.get_announce_by_hash(destination_hash)
        if db_announce and db_announce["aspect"] == "nomadnetwork.node":
            node_name = parse_nomadnetwork_node_display_name(db_announce["app_data"])
    return node_name or "Unknown Node"
