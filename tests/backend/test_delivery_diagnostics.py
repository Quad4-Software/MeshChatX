# SPDX-License-Identifier: 0BSD
"""Oracles for delivery diagnostics snapshots and HTTP route."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.delivery_diagnostics import build_delivery_diagnostics


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(match_info=None):
    request = MagicMock()
    request.match_info = match_info or {}
    return request


def test_build_delivery_diagnostics_auto_announce_disabled(mock_app):
    mock_app.current_context.config.auto_announce_enabled.set(False)
    mock_app.current_context.config.auto_announce_interval_seconds.set(0)
    mock_app.current_context.config.last_announced_at.set(int(time.time()))
    mock_app.recall_identity = MagicMock(return_value=None)
    mock_app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    mock_app.message_router = MagicMock()
    mock_app.message_router.get_outbound_ticket_expiry.return_value = None

    peer = "ab" * 16
    with (
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.has_path",
            return_value=False,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.rp.path_metadata_for_api",
            return_value={"path_stale": True, "path_unresponsive": False},
        ),
    ):
        data = build_delivery_diagnostics(mock_app, peer)

    assert data["self"]["auto_announce_enabled"] is False
    assert "propagation_node" in data
    assert data["propagation_node"]["configured"] is False
    print("DELIVERY_DIAG_AUTO_ANNOUNCE_OFF_ORACLE_PROVED")


def test_build_delivery_diagnostics_peer_announce_missing(mock_app):
    mock_app.current_context.config.auto_announce_enabled.set(True)
    mock_app.recall_identity = MagicMock(return_value=None)
    mock_app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    mock_app.database.announces.get_announce_by_hash = MagicMock(return_value=None)
    mock_app.database.announces.get_filtered_announces = MagicMock(return_value=[])
    mock_app.message_router = MagicMock()
    mock_app.message_router.get_outbound_ticket_expiry.return_value = None

    peer = "cd" * 16
    with (
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.has_path",
            return_value=False,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.rp.path_metadata_for_api",
            return_value={"path_stale": True, "path_unresponsive": False},
        ),
    ):
        data = build_delivery_diagnostics(mock_app, peer)

    assert data["peer_announce"]["known"] is False
    print("DELIVERY_DIAG_PEER_ANNOUNCE_MISSING_ORACLE_PROVED")


def test_build_delivery_diagnostics_path_available(mock_app):
    identity = RNS.Identity()
    identity_hex = identity.hash.hex()
    delivery_hex = RNS.Destination.hash(identity, "lxmf", "delivery").hex()
    delivery_bytes = bytes.fromhex(delivery_hex)

    mock_app.get_lxmf_destination_hash_for_identity_hash = MagicMock(
        return_value=delivery_hex
    )
    mock_app.recall_identity = MagicMock(return_value=identity)
    mock_app.database.announces.get_announce_by_hash = MagicMock(
        return_value={"updated_at": "2026-01-01T00:00:00"}
    )
    mock_app.message_router = MagicMock()
    mock_app.message_router.get_outbound_ticket_expiry.return_value = None

    with (
        patch(
            "meshchatx.src.backend.delivery_diagnostics._lxmf_delivery_hash_bytes_for_path",
            return_value=delivery_bytes,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics._lxmf_delivery_hash_hex_for_path",
            return_value=delivery_hex,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.has_path",
            return_value=True,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.hops_to",
            return_value=2,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.rp.path_metadata_for_api",
            return_value={"path_stale": False, "path_unresponsive": False},
        ),
    ):
        data = build_delivery_diagnostics(mock_app, identity_hex)

    assert data["path"]["has_path"] is True
    assert data["path"]["hops"] == 2
    assert "propagation_node" in data
    print("DELIVERY_DIAG_PATH_AVAILABLE_ORACLE_PROVED")


def test_build_delivery_diagnostics_propagation_node_path(mock_app):
    prop = b"\x11" * 16
    mock_app.recall_identity = MagicMock(return_value=None)
    mock_app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    mock_app.database.announces.get_announce_by_hash = MagicMock(return_value=None)
    mock_app.database.announces.get_filtered_announces = MagicMock(return_value=[])
    mock_app.message_router = MagicMock()
    mock_app.message_router.get_outbound_ticket_expiry.return_value = None
    mock_app.message_router.get_outbound_propagation_node.return_value = prop
    mock_app.message_router.propagation_destination = MagicMock(hash=b"\x22" * 16)

    peer = "ab" * 16

    def _has_path(dest):
        return bytes(dest) == prop

    with (
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.has_path",
            side_effect=_has_path,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.hops_to",
            return_value=1,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.rp.path_metadata_for_api",
            return_value={"path_stale": False, "path_unresponsive": False},
        ),
    ):
        data = build_delivery_diagnostics(
            mock_app,
            peer,
            failure_hint="no_path_propagation_node",
        )

    assert data["propagation_node"]["configured"] is True
    assert data["propagation_node"]["destination_hash"] == prop.hex()
    assert data["propagation_node"]["has_path"] is True
    assert data["propagation_node"]["is_local"] is False
    assert data["failure_hint"] == "no_path_propagation_node"
    print("DELIVERY_DIAG_PROP_NODE_ORACLE_PROVED")


@pytest.mark.asyncio
async def test_delivery_diagnostics_http_route(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/delivery-diagnostics",
        "GET",
    )
    assert handler is not None

    peer = "ef" * 16
    mock_app.recall_identity = MagicMock(return_value=None)
    mock_app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    mock_app.database.announces.get_announce_by_hash = MagicMock(return_value=None)
    mock_app.database.announces.get_filtered_announces = MagicMock(return_value=[])
    mock_app.message_router = MagicMock()
    mock_app.message_router.get_outbound_ticket_expiry.return_value = None

    with (
        patch(
            "meshchatx.src.backend.delivery_diagnostics.RNS.Transport.has_path",
            return_value=False,
        ),
        patch(
            "meshchatx.src.backend.delivery_diagnostics.rp.path_metadata_for_api",
            return_value={"path_stale": True, "path_unresponsive": False},
        ),
    ):
        response = await handler(_make_request(match_info={"destination_hash": peer}))

    assert response.status == 200
    payload = json.loads(response.body)
    assert payload["peer"]["input_hash"] == peer
    assert "path" in payload
    print("DELIVERY_DIAG_HTTP_ROUTE_ORACLE_PROVED")
