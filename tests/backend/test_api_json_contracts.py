"""JSON Schema contract tests for core HTTP API responses."""

from __future__ import annotations

import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from tests.backend.api_json_contract_schemas import (
    API_V1_APP_INFO_ENVELOPE_SCHEMA,
    API_V1_STATUS_SCHEMA,
    AUTH_STATUS_SCHEMA,
    assert_matches_schema,
)


@pytest.fixture(autouse=True)
def _stub_threads_for_http_contract_tests():
    with patch("threading.Thread"):
        yield


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


def _route_handler(app: ReticulumMeshChat, path: str, method: str):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


@pytest.mark.asyncio
async def test_api_v1_status_json_contract(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _route_handler(app_instance, "/api/v1/status", "GET")
        assert handler is not None
        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, API_V1_STATUS_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_app_info_json_contract(mock_rns_minimal, temp_dir):
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("psutil.Process") as mock_process,
        patch("psutil.net_io_counters") as mock_net_io,
        patch("importlib.metadata.version", return_value="1.2.3"),
        patch("meshchatx.meshchat.LXST") as mock_lxst,
    ):
        mock_lxst.__version__ = "1.2.3"

        mock_proc_instance = mock_process.return_value
        mock_proc_instance.memory_info.return_value.rss = 1024
        mock_proc_instance.memory_info.return_value.vms = 2048
        mock_proc_instance.net_connections.return_value = []

        mock_net_instance = mock_net_io.return_value
        mock_net_instance.bytes_sent = 0
        mock_net_instance.bytes_recv = 0
        mock_net_instance.packets_sent = 0
        mock_net_instance.packets_recv = 0

        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        handler = _route_handler(app_instance, "/api/v1/app/info", "GET")
        assert handler is not None
        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, API_V1_APP_INFO_ENVELOPE_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_auth_status_json_contract(mock_rns_minimal, temp_dir):
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("meshchatx.meshchat.get_session", new_callable=AsyncMock) as mock_session,
    ):
        mock_session.return_value = {
            "authenticated": False,
            "identity_hash": None,
        }

        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        handler = _route_handler(app_instance, "/api/v1/auth/status", "GET")
        assert handler is not None
        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, AUTH_STATUS_SCHEMA)


def test_auth_status_schema_accepts_error_envelope():
    sample = {
        "auth_enabled": True,
        "password_set": True,
        "authenticated": False,
        "error": "decryption failed",
    }
    assert_matches_schema(sample, AUTH_STATUS_SCHEMA)
