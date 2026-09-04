# SPDX-License-Identifier: 0BSD
"""Oracles for identity hash to lxmf.delivery resolution on path and ping APIs."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.http.routes.path_probe import (
    lxmf_delivery_hash_bytes_for_path,
    lxmf_delivery_hash_hex_for_path,
)


@pytest.fixture
def auto_resend_db(tmp_path):
    path = str(tmp_path / "path_probe_resolve.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(match_info=None, query=None, method="POST"):
    request = MagicMock()
    request.match_info = match_info or {}
    request.query = query or {}
    request.method = method
    return request


def test_lxmf_delivery_hash_bytes_for_path_resolves_identity():
    identity = RNS.Identity()
    identity_hex = identity.hash.hex()
    delivery_hex = RNS.Destination.hash(identity, "lxmf", "delivery").hex()
    assert identity_hex != delivery_hex

    app = MagicMock()
    app.get_lxmf_destination_hash_for_identity_hash.return_value = delivery_hex

    resolved = lxmf_delivery_hash_bytes_for_path(app, identity_hex)
    assert resolved == bytes.fromhex(delivery_hex)
    assert lxmf_delivery_hash_hex_for_path(app, identity_hex) == delivery_hex
    print("PATH_PROBE_IDENTITY_TO_DELIVERY_ORACLE_PROVED")


def test_lxmf_delivery_hash_bytes_for_path_keeps_unknown_hash():
    app = MagicMock()
    app.get_lxmf_destination_hash_for_identity_hash.return_value = None
    raw = "ab" * 16
    assert lxmf_delivery_hash_bytes_for_path(app, raw) == bytes.fromhex(raw)


@pytest.mark.asyncio
async def test_post_path_waits_on_lxmf_delivery_when_identity_passed(mock_app):
    identity = RNS.Identity()
    identity_hex = identity.hash.hex()
    delivery_hex = RNS.Destination.hash(identity, "lxmf", "delivery").hex()
    delivery_bytes = bytes.fromhex(delivery_hex)

    mock_app.reticulum = MagicMock()
    mock_app.reticulum.get_next_hop.return_value = bytes(16)
    mock_app.reticulum.get_next_hop_if_name.return_value = "if0"

    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/path",
        "POST",
    )
    req = _make_request(
        match_info={"destination_hash": identity_hex},
        query={"timeout": "1"},
    )

    with (
        patch(
            "meshchatx.src.backend.http.routes.path_probe.lxmf_delivery_hash_bytes_for_path",
            return_value=delivery_bytes,
        ),
        patch(
            "meshchatx.src.backend.http.routes.path_probe.local_destination_hashes",
            return_value=set(),
        ),
        patch(
            "meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request",
        ) as prepare,
        patch(
            "meshchatx.meshchat.reticulum_pathfinding.path_metadata_for_api",
            return_value={"path_stale": False, "path_unresponsive": False},
        ),
        patch(
            "meshchatx.meshchat.RNS.Transport.has_path",
            side_effect=lambda dest: dest == delivery_bytes,
        ),
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=2),
        patch("meshchatx.meshchat.asyncio.sleep", new_callable=AsyncMock),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        response = await handler(req)

    assert response.status == 200
    prepare.assert_called_once()
    assert prepare.call_args[0][1] == delivery_bytes
    data = json.loads(response.body)
    assert data["path"]["hops"] == 2


@pytest.mark.asyncio
async def test_ping_waits_on_lxmf_delivery_when_identity_passed(mock_app):
    identity = RNS.Identity()
    identity_hex = identity.hash.hex()
    delivery_hex = RNS.Destination.hash(identity, "lxmf", "delivery").hex()
    delivery_bytes = bytes.fromhex(delivery_hex)

    mock_app.reticulum = MagicMock()
    mock_app.recall_identity = MagicMock(return_value=identity)

    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "POST",
    )

    receipt = MagicMock()
    receipt.status = RNS.PacketReceipt.DELIVERED
    receipt.proof_packet.hops = 1
    receipt.proof_packet.rssi = -50
    receipt.proof_packet.snr = 5
    receipt.proof_packet.q = 100
    receipt.proof_packet.receiving_interface = "TCP"
    receipt.proof_packet.packet_hash = b"\x00" * 16
    receipt.get_rtt.return_value = 0.1
    receipt.destination.hash.hex.return_value = delivery_hex
    packet = MagicMock()
    packet.send.return_value = receipt

    path_checks: list[bytes] = []

    def _has_path(dest):
        path_checks.append(dest)
        return dest == delivery_bytes

    with (
        patch(
            "meshchatx.src.backend.http.routes.path_probe.lxmf_delivery_hash_bytes_for_path",
            return_value=delivery_bytes,
        ),
        patch("meshchatx.meshchat.RNS.Transport.has_path", side_effect=_has_path),
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=1),
        patch("meshchatx.meshchat.RNS.Destination"),
        patch("meshchatx.meshchat.RNS.Packet", return_value=packet),
        patch("meshchatx.meshchat.asyncio.sleep", new_callable=AsyncMock),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        response = await handler(
            _make_request(
                match_info={"destination_hash": identity_hex},
                query={"timeout": "5"},
            ),
        )

    assert response.status == 200
    assert delivery_bytes in path_checks


@pytest.mark.asyncio
async def test_request_path_resend_uses_lxmf_delivery_lookup(mock_app):
    identity = RNS.Identity()
    identity_hex = identity.hash.hex()
    delivery_hex = RNS.Destination.hash(identity, "lxmf", "delivery").hex()
    delivery_bytes = bytes.fromhex(delivery_hex)

    current = MagicMock()
    current.running = True
    current.config.auto_resend_failed_messages_when_announce_received.get.return_value = True
    mock_app.current_context = current
    mock_app.resend_failed_messages_for_destination = MagicMock(
        return_value=MagicMock(),
    )

    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/request-path",
        "POST",
    )

    with (
        patch(
            "meshchatx.src.backend.http.routes.path_probe.lxmf_delivery_hash_bytes_for_path",
            return_value=delivery_bytes,
        ),
        patch(
            "meshchatx.src.backend.http.routes.path_probe.lxmf_delivery_hash_hex_for_path",
            return_value=delivery_hex,
        ),
        patch("meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request"),
        patch(
            "meshchatx.meshchat.RNS.Transport.has_path",
            side_effect=lambda dest: dest == delivery_bytes,
        ),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        response = await handler(
            _make_request(match_info={"destination_hash": identity_hex}),
        )

    assert response.status == 200
    mock_app.resend_failed_messages_for_destination.assert_called_once()
    call = mock_app.resend_failed_messages_for_destination.call_args
    dest_arg = call.kwargs.get("destination_hash") or call.args[0]
    assert dest_arg == delivery_hex


@pytest.mark.asyncio
async def test_resend_failed_lookup_uses_lxmf_delivery_for_identity(auto_resend_db):
    import types

    from meshchatx.meshchat import ReticulumMeshChat
    from meshchatx.src.backend import auto_resend_guard as guard

    identity = RNS.Identity()
    identity_hex = identity.hash.hex()
    delivery_hex = RNS.Destination.hash(identity, "lxmf", "delivery").hex()

    app = MagicMock()
    app._auto_resend_coordinator = guard.AutoResendCoordinator()
    app.websocket_broadcast = AsyncMock()
    app.resend_failed_messages_for_destination = types.MethodType(
        ReticulumMeshChat.resend_failed_messages_for_destination,
        app,
    )
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(
        return_value=delivery_hex,
    )

    ctx = MagicMock()
    ctx.identity.hash.hex.return_value = "aa" * 16
    ctx.database = auto_resend_db
    ctx.config.allow_auto_resending_failed_messages_with_attachments.get.return_value = True

    auto_resend_db.messages.upsert_lxmf_message(
        {
            "hash": "ff" * 16,
            "source_hash": "aa" * 16,
            "destination_hash": delivery_hex,
            "peer_hash": delivery_hex,
            "state": "failed",
            "progress": 0,
            "is_incoming": 0,
            "method": "direct",
            "delivery_attempts": 1,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": "retry me",
            "fields": "{}",
            "timestamp": 1.0,
        },
    )

    new_msg = MagicMock()
    new_msg.hash = b"\x01" * 16
    app.send_message = AsyncMock(return_value=new_msg)

    await app.resend_failed_messages_for_destination(identity_hex, context=ctx)
    app.send_message.assert_awaited_once()
    call = app.send_message.await_args
    dest_arg = call.kwargs.get("destination_hash") or call.args[0]
    assert dest_arg == delivery_hex
