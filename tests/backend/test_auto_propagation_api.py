# SPDX-License-Identifier: 0BSD

import asyncio
import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter") as mock_lxmf_router,
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
        patch("meshchatx.meshchat.generate_ssl_certificate"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        # Mock LXMF router and its return values to be JSON serializable
        mock_lxmf_router_instance = mock_lxmf_router.return_value
        mock_dest = MagicMock()
        mock_dest.hexhash = "test_lxmf_hexhash"
        mock_lxmf_router_instance.register_delivery_identity.return_value = mock_dest
        mock_lxmf_router_instance.propagation_destination = mock_dest

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        mock_id.get_public_key.return_value = b"test_public_key_32_bytes_long!!!!"
        yield mock_id


@pytest.mark.asyncio
async def test_auto_propagation_api(mock_rns_minimal, temp_dir):
    app_instance = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # 1. Test GET /api/v1/config includes auto_select
    get_handler = None
    for route in app_instance.get_routes():
        if route.path == "/api/v1/config" and route.method == "GET":
            get_handler = route.handler
            break

    assert get_handler is not None
    request = MagicMock()
    response = await get_handler(request)
    data = json.loads(response.body)
    assert "lxmf_preferred_propagation_node_auto_select" in data["config"]
    assert data["config"]["lxmf_preferred_propagation_node_auto_select"] is False
    assert "lxmf_propagation_transfer_limit_in_bytes" in data["config"]
    assert "lxmf_propagation_sync_limit_in_bytes" in data["config"]

    # 2. Test PATCH /api/v1/config updates auto_select
    patch_handler = None
    for route in app_instance.get_routes():
        if route.path == "/api/v1/config" and route.method == "PATCH":
            patch_handler = route.handler
            break

    assert patch_handler is not None

    # Update to True
    mock_request = MagicMock()
    mock_request.json = MagicMock(return_value=asyncio.Future())
    mock_request.json.return_value.set_result(
        {"lxmf_preferred_propagation_node_auto_select": True},
    )

    response = await patch_handler(mock_request)
    data = json.loads(response.body)
    assert data["config"]["lxmf_preferred_propagation_node_auto_select"] is True
    assert app_instance.config.lxmf_preferred_propagation_node_auto_select.get() is True

    # Update to False
    mock_request = MagicMock()
    mock_request.json = MagicMock(return_value=asyncio.Future())
    mock_request.json.return_value.set_result(
        {"lxmf_preferred_propagation_node_auto_select": False},
    )

    response = await patch_handler(mock_request)
    data = json.loads(response.body)
    assert data["config"]["lxmf_preferred_propagation_node_auto_select"] is False
    assert (
        app_instance.config.lxmf_preferred_propagation_node_auto_select.get() is False
    )

    # Update transfer/sync limits and validate clamping/application
    mock_request = MagicMock()
    mock_request.json = MagicMock(return_value=asyncio.Future())
    mock_request.json.return_value.set_result(
        {
            "lxmf_propagation_transfer_limit_in_bytes": 250_000,
            "lxmf_propagation_sync_limit_in_bytes": 9_000_000,
        },
    )

    response = await patch_handler(mock_request)
    data = json.loads(response.body)
    assert data["config"]["lxmf_propagation_transfer_limit_in_bytes"] == 250_000
    assert data["config"]["lxmf_propagation_sync_limit_in_bytes"] == 9_000_000
    assert app_instance.config.lxmf_propagation_transfer_limit_in_bytes.get() == 250_000
    assert app_instance.config.lxmf_propagation_sync_limit_in_bytes.get() == 9_000_000

    mock_request = MagicMock()
    mock_request.json = MagicMock(return_value=asyncio.Future())
    mock_request.json.return_value.set_result(
        {"lxmf_delivery_transfer_limit_in_bytes": 2_000_000_000},
    )

    response = await patch_handler(mock_request)
    data = json.loads(response.body)
    assert data["config"]["lxmf_delivery_transfer_limit_in_bytes"] == 1_000_000_000
    assert (
        app_instance.config.lxmf_delivery_transfer_limit_in_bytes.get() == 1_000_000_000
    )
    assert app_instance.message_router.delivery_per_transfer_limit == 1_000_000
