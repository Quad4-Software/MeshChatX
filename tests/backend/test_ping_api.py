# SPDX-License-Identifier: 0BSD

"""Regression tests for the LXMF delivery ping HTTP endpoint."""

import json
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.http.routes.path_probe import PATH_WAIT_REQUIRES_POST_MESSAGE


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


def _two_running_contexts(mock_app):
    current = MagicMock()
    current.running = True
    current.config.auto_resend_failed_messages_when_announce_received.get.return_value = True
    other = MagicMock()
    other.running = True
    other.config.auto_resend_failed_messages_when_announce_received.get.return_value = (
        True
    )
    mock_app.current_context = current
    mock_app.contexts = {"current": current, "other": other}
    mock_app.resend_failed_messages_for_destination = MagicMock(
        return_value=MagicMock(),
    )
    return current, other


@pytest.mark.asyncio
async def test_ping_is_post_not_get(mock_app):
    path = "/api/v1/ping/{destination_hash}/lxmf.delivery"
    assert _find_handler(mock_app, path, "POST") is not None
    assert _find_handler(mock_app, path, "GET") is None


@pytest.mark.asyncio
async def test_ping_rejects_invalid_destination_hash(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "POST",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "not-hex"},
            query={"timeout": "5"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "Invalid destination hash" in data["message"]


@pytest.mark.asyncio
async def test_ping_rejects_non_integer_timeout(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "POST",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "abc"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "Timeout" in data["message"]


@pytest.mark.asyncio
async def test_ping_rejects_zero_timeout(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "POST",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "0"},
        ),
    )
    assert response.status == 400


@pytest.mark.asyncio
async def test_ping_rejects_timeout_above_600(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "POST",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "601"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "600" in data["message"]


@pytest.mark.asyncio
async def test_get_path_request_true_is_400_and_does_not_prepare(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/path",
        "GET",
    )
    assert handler is not None
    dest = "a" * 32
    req = _make_request(
        match_info={"destination_hash": dest},
        query={"request": "true", "timeout": "1"},
        method="GET",
    )
    with patch(
        "meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request",
    ) as pfp:
        response = await handler(req)
    assert response.status == 400
    data = json.loads(response.body)
    assert data["message"] == PATH_WAIT_REQUIRES_POST_MESSAGE
    pfp.assert_not_called()


@pytest.mark.asyncio
async def test_post_path_rejects_timeout_above_600(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/path",
        "POST",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "601"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "600" in data["message"]


@pytest.mark.asyncio
async def test_post_path_rejects_non_integer_timeout(mock_app):
    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/path",
        "POST",
    )
    assert handler is not None
    response = await handler(
        _make_request(
            match_info={"destination_hash": "ab" * 16},
            query={"timeout": "nope"},
        ),
    )
    assert response.status == 400
    data = json.loads(response.body)
    assert "integer" in data["message"].lower()


@pytest.mark.asyncio
async def test_request_path_resend_uses_current_context_only(mock_app):
    current, other = _two_running_contexts(mock_app)
    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/request-path",
        "POST",
    )
    dest = "b" * 32
    req = _make_request(match_info={"destination_hash": dest})
    with (
        patch("meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request"),
        patch("meshchatx.meshchat.RNS.Transport.has_path", return_value=True),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        response = await handler(req)
    assert response.status == 200
    mock_app.resend_failed_messages_for_destination.assert_called_once()
    kwargs = mock_app.resend_failed_messages_for_destination.call_args.kwargs
    assert kwargs["context"] is current
    assert kwargs["context"] is not other


@pytest.mark.asyncio
async def test_post_path_resend_uses_current_context_only(mock_app):
    current, other = _two_running_contexts(mock_app)
    mock_app.reticulum = MagicMock()
    mock_app.reticulum.get_next_hop.return_value = bytes(16)
    mock_app.reticulum.get_next_hop_if_name.return_value = "if0"
    handler = _find_handler(
        mock_app,
        "/api/v1/destination/{destination_hash}/path",
        "POST",
    )
    dest = "c" * 32
    req = _make_request(
        match_info={"destination_hash": dest},
        query={"timeout": "1"},
    )
    with (
        patch("meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request"),
        patch(
            "meshchatx.meshchat.reticulum_pathfinding.path_metadata_for_api",
            return_value={"path_stale": False, "path_unresponsive": False},
        ),
        patch("meshchatx.meshchat.RNS.Transport.has_path", return_value=True),
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=2),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        response = await handler(req)
    assert response.status == 200
    mock_app.resend_failed_messages_for_destination.assert_called_once()
    kwargs = mock_app.resend_failed_messages_for_destination.call_args.kwargs
    assert kwargs["context"] is current
    assert kwargs["context"] is not other


@pytest.mark.asyncio
async def test_ping_resend_uses_current_context_only(mock_app):
    import RNS

    current, other = _two_running_contexts(mock_app)
    mock_app.reticulum = MagicMock()
    mock_app.recall_identity = MagicMock(return_value=MagicMock())
    handler = _find_handler(
        mock_app,
        "/api/v1/ping/{destination_hash}/lxmf.delivery",
        "POST",
    )
    dest = "ab" * 16
    receipt = MagicMock()
    receipt.status = RNS.PacketReceipt.DELIVERED
    receipt.proof_packet.hops = 1
    receipt.proof_packet.rssi = -50
    receipt.proof_packet.snr = 5
    receipt.proof_packet.q = 100
    receipt.proof_packet.receiving_interface = "UDP"
    receipt.proof_packet.packet_hash = b"\x00" * 16
    receipt.get_rtt.return_value = 0.1
    receipt.destination.hash.hex.return_value = dest
    packet = MagicMock()
    packet.send.return_value = receipt

    with (
        patch("meshchatx.meshchat.RNS.Transport.has_path", return_value=True),
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=1),
        patch("meshchatx.meshchat.RNS.Destination"),
        patch("meshchatx.meshchat.RNS.Packet", return_value=packet),
        patch("meshchatx.meshchat.AsyncUtils.run_async"),
    ):
        response = await handler(
            _make_request(
                match_info={"destination_hash": dest},
                query={"timeout": "5"},
            ),
        )
    assert response.status == 200
    mock_app.resend_failed_messages_for_destination.assert_called_once()
    kwargs = mock_app.resend_failed_messages_for_destination.call_args.kwargs
    assert kwargs["context"] is current
    assert kwargs["context"] is not other
