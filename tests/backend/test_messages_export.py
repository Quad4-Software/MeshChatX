# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


def _make_json_request(body):
    request = MagicMock()

    async def _json():
        return body

    request.json = _json
    return request


def _make_multipart_file_request(body: bytes):
    class _MultipartField:
        name = "file"

        def __init__(self, data):
            self._data = data
            self._offset = 0

        async def read_chunk(self, size=1024 * 1024):
            if self._offset >= len(self._data):
                return b""
            chunk = self._data[self._offset : self._offset + size]
            self._offset += len(chunk)
            return chunk

    class _MultipartReader:
        def __init__(self, field):
            self._field = field
            self._done = False

        async def next(self):
            if self._done:
                return None
            self._done = True
            return self._field

    request = MagicMock()

    async def _multipart():
        return _MultipartReader(_MultipartField(body))

    request.multipart = _multipart
    return request


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


@pytest.mark.asyncio
async def test_messages_import_export_roundtrip(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app.database.messages.upsert_lxmf_message(
            {
                "hash": "40509ace976b2e572bff2944d60207218135ef69940a25a423e60615760e7e06",
                "source_hash": "695ff7ffdd5f9ef1ae7772cfa2ecf028",
                "destination_hash": "7cc8d66b4f6a0e0e49d34af7f6077b5a",
                "peer_hash": "695ff7ffdd5f9ef1ae7772cfa2ecf028",
                "state": "generating",
                "progress": 0,
                "is_incoming": 1,
                "method": "opportunistic",
                "delivery_attempts": 0,
                "next_delivery_attempt_at": None,
                "title": "",
                "content": "i ran nomadnet on orange pi lite too",
                "fields": "{}",
                "timestamp": 1773512977.322906,
                "rssi": None,
                "snr": None,
                "quality": None,
                "is_spam": 0,
                "reply_to_hash": None,
                "attachments_stripped": 0,
            },
        )

        export_handler = None
        import_handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/maintenance/messages/export"
                and route.method == "GET"
            ):
                export_handler = route.handler
            if (
                route.path == "/api/v1/maintenance/messages/import"
                and route.method == "POST"
            ):
                import_handler = route.handler
        assert export_handler is not None
        assert import_handler is not None

        export_response = await export_handler(MagicMock())
        export_data = json.loads(export_response.body)
        assert len(export_data["messages"]) == 1
        assert "lxmf_icon" not in export_data["messages"][0]

        import_response = await import_handler(
            _make_json_request({"messages": export_data["messages"]}),
        )
        assert import_response.status == 200
        import_data = json.loads(import_response.body)
        assert import_data["imported"] == 1
        assert import_data["skipped"] == 0


@pytest.mark.asyncio
async def test_messages_import_file_upload(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        import_file_handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/maintenance/messages/import-file"
                and route.method == "POST"
            ):
                import_file_handler = route.handler
                break
        assert import_file_handler is not None

        payload = {
            "messages": [
                {
                    "hash": "40509ace976b2e572bff2944d60207218135ef69940a25a423e60615760e7e06",
                    "source_hash": "695ff7ffdd5f9ef1ae7772cfa2ecf028",
                    "destination_hash": "7cc8d66b4f6a0e0e49d34af7f6077b5a",
                    "peer_hash": "695ff7ffdd5f9ef1ae7772cfa2ecf028",
                    "state": "generating",
                    "progress": 0,
                    "is_incoming": 1,
                    "method": "opportunistic",
                    "fields": "{}",
                    "timestamp": 1773512977.322906,
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        response = await import_file_handler(_make_multipart_file_request(body))
        assert response.status == 200
        data = json.loads(response.body)
        assert data["imported"] == 1
