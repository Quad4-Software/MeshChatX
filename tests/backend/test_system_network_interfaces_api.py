# SPDX-License-Identifier: 0BSD

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
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_system_network_interfaces_returns_json(mock_rns_minimal, temp_dir):
    fake_ifaces = (
        [
            {"name": "eth0", "addresses": []},
            {"name": "lo", "addresses": []},
        ],
        None,
    )
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch(
            "meshchatx.meshchat.list_host_network_interfaces", return_value=fake_ifaces
        ),
    ):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app_instance.get_routes():
            if (
                route.path == "/api/v1/system/network-interfaces"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None
        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert data["interfaces"] == [
            {"name": "eth0", "addresses": []},
            {"name": "lo", "addresses": []},
        ]
        assert data["unavailable_reason"] is None


@pytest.mark.asyncio
async def test_system_network_interfaces_surfaces_psutil_error(
    mock_rns_minimal, temp_dir
):
    fake_ifaces = ([], "permission denied")
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch(
            "meshchatx.meshchat.list_host_network_interfaces", return_value=fake_ifaces
        ),
    ):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app_instance.get_routes():
            if (
                route.path == "/api/v1/system/network-interfaces"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None
        response = await handler(MagicMock())
        data = json.loads(response.body)
        assert data["interfaces"] == []
        assert data["unavailable_reason"] == "permission denied"
