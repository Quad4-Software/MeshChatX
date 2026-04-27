# SPDX-License-Identifier: 0BSD

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_destination_path_with_request_calls_prepare_fresh(mock_app):
    mock_app.reticulum = MagicMock()
    mock_app.reticulum.get_next_hop.return_value = bytes(16)
    mock_app.reticulum.get_next_hop_if_name.return_value = "if0"
    h = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/destination/{destination_hash}/path"
    )
    dest = "a" * 32
    req = SimpleNamespace(
        match_info={"destination_hash": dest},
        query={"request": "1", "timeout": "1"},
    )
    with (
        patch(
            "meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request",
        ) as pfp,
        patch(
            "meshchatx.meshchat.reticulum_pathfinding.path_metadata_for_api",
            return_value={"path_stale": False, "path_unresponsive": False},
        ),
        patch("meshchatx.meshchat.RNS.Transport.has_path", return_value=True),
        patch("meshchatx.meshchat.RNS.Transport.hops_to", return_value=2),
        patch("meshchatx.meshchat.asyncio.sleep", new_callable=AsyncMock),
    ):
        response = await h(req)
    pfp.assert_called_once()
    assert pfp.call_args[0][0] is mock_app.reticulum
    assert pfp.call_args[0][1] == bytes.fromhex(dest)
    data = json.loads(response.body)
    assert data["path"]["hops"] == 2
    assert data["path_stale"] is False
    assert data["path_unresponsive"] is False


@pytest.mark.asyncio
async def test_post_destination_request_path_calls_prepare_fresh(mock_app):
    mock_app.reticulum = MagicMock()
    h = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/destination/{destination_hash}/request-path"
    )
    dest = "b" * 32
    req = SimpleNamespace(match_info={"destination_hash": dest})
    with patch(
        "meshchatx.meshchat.reticulum_pathfinding.prepare_fresh_path_request",
    ) as pfp:
        response = await h(req)
    pfp.assert_called_once()
    assert pfp.call_args[0][0] is mock_app.reticulum
    assert pfp.call_args[0][1] == bytes.fromhex(dest)
    assert response.status == 200
    data = json.loads(response.body)
    assert data["message"] == "ok"
