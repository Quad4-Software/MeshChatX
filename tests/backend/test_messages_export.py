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
async def test_messages_export_with_icons(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app.database.messages.upsert_lxmf_message(
            {
                "hash": "msg1",
                "source_hash": "peer1",
                "destination_hash": "local",
                "peer_hash": "peer1",
                "state": "delivered",
                "progress": 1.0,
                "is_incoming": 1,
                "method": "delivery",
                "delivery_attempts": 0,
                "next_delivery_attempt_at": None,
                "title": None,
                "content": "Hello",
                "fields": None,
                "timestamp": 1000.0,
                "rssi": None,
                "snr": None,
                "quality": None,
                "is_spam": 0,
                "reply_to_hash": None,
                "attachments_stripped": None,
                "path_hops_at_send": None,
                "path_interface_at_send": None,
                "path_finding_measure": None,
                "path_row_hash_hex": None,
            }
        )
        app.database.messages.upsert_lxmf_message(
            {
                "hash": "msg2",
                "source_hash": "local",
                "destination_hash": "peer2",
                "peer_hash": "peer2",
                "state": "delivered",
                "progress": 1.0,
                "is_incoming": 0,
                "method": "delivery",
                "delivery_attempts": 0,
                "next_delivery_attempt_at": None,
                "title": None,
                "content": "World",
                "fields": None,
                "timestamp": 2000.0,
                "rssi": None,
                "snr": None,
                "quality": None,
                "is_spam": 0,
                "reply_to_hash": None,
                "attachments_stripped": None,
                "path_hops_at_send": None,
                "path_interface_at_send": None,
                "path_finding_measure": None,
                "path_row_hash_hex": None,
            }
        )
        app.database.misc.update_lxmf_user_icon(
            "peer1", "account", "#FFFFFF", "#000000"
        )
        app.database.misc.update_lxmf_user_icon("peer2", "robot", "#000000", "#FFFFFF")

        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/maintenance/messages/export"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert "messages" in data
        assert len(data["messages"]) == 2

        msg1 = next(m for m in data["messages"] if m["hash"] == "msg1")
        assert "lxmf_icon" in msg1
        assert msg1["lxmf_icon"]["icon_name"] == "account"

        msg2 = next(m for m in data["messages"] if m["hash"] == "msg2")
        assert "lxmf_icon" in msg2
        assert msg2["lxmf_icon"]["icon_name"] == "robot"


@pytest.mark.asyncio
async def test_messages_export_without_icons(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app.database.messages.upsert_lxmf_message(
            {
                "hash": "msg1",
                "source_hash": "peer1",
                "destination_hash": "local",
                "peer_hash": "peer1",
                "state": "delivered",
                "progress": 1.0,
                "is_incoming": 1,
                "method": "delivery",
                "delivery_attempts": 0,
                "next_delivery_attempt_at": None,
                "title": None,
                "content": "Hello",
                "fields": None,
                "timestamp": 1000.0,
                "rssi": None,
                "snr": None,
                "quality": None,
                "is_spam": 0,
                "reply_to_hash": None,
                "attachments_stripped": None,
                "path_hops_at_send": None,
                "path_interface_at_send": None,
                "path_finding_measure": None,
                "path_row_hash_hex": None,
            }
        )

        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/maintenance/messages/export"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert len(data["messages"]) == 1
        assert "lxmf_icon" not in data["messages"][0]
