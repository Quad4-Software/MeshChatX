# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

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

        mock_id = MagicMock()
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_interface_stats_serializes_bytes_and_parent_hash_null(
    mock_rns_minimal, temp_dir
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reticulum = MagicMock()
        app_instance.reticulum.get_interface_stats.return_value = {
            "interfaces": [
                {
                    "short_name": "Child",
                    "status": True,
                    "parent_interface_name": "Parent",
                    "parent_interface_hash": None,
                    "hash": b"\x01" * 16,
                    "ifac_signature": b"\x02" * 16,
                },
                {
                    "short_name": "Main",
                    "status": True,
                    "hash": b"\x03" * 16,
                },
            ],
            "transport_id": b"\x04" * 16,
            "network_id": b"\x05" * 16,
            "probe_responder": b"\x06" * 16,
        }

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/interface-stats" and route.method == "GET":
                handler = route.handler
                break

        assert handler is not None

        response = await handler(MagicMock())
        assert response.status == 200
        data = json.loads(response.body)
        stats = data["interface_stats"]

        assert stats["transport_id"] == ("04" * 16)
        assert stats["network_id"] == ("05" * 16)
        assert stats["probe_responder"] == ("06" * 16)
        assert len(stats["interfaces"]) == 2
        assert stats["interfaces"][0]["interface_name"] == "Child"
        assert stats["interfaces"][0]["parent_interface_hash"] is None
        assert stats["interfaces"][0]["hash"] == ("01" * 16)
        assert stats["interfaces"][1]["short_name"] == "Main"
