# SPDX-License-Identifier: 0BSD

"""JSON Schema contract tests for telephone phonebook, ringtones, and voicemail APIs."""

from __future__ import annotations

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from tests.backend.api_json_contract_schemas import (
    TELEPHONE_CONTACT_CHECK_SCHEMA,
    TELEPHONE_CONTACTS_LIST_SCHEMA,
    TELEPHONE_RINGTONE_STATUS_SCHEMA,
    TELEPHONE_RINGTONES_LIST_SCHEMA,
    TELEPHONE_VOICEMAIL_STATUS_SCHEMA,
    TELEPHONE_VOICEMAILS_ENVELOPE_SCHEMA,
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


def _find_handler(app: ReticulumMeshChat, path: str, method: str):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


class _Query:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


@pytest.mark.asyncio
async def test_api_v1_telephone_voicemail_status_json_contract(
    mock_rns_minimal, temp_dir
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _find_handler(
            app_instance, "/api/v1/telephone/voicemail/status", "GET"
        )
        assert handler is not None
        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, TELEPHONE_VOICEMAIL_STATUS_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_telephone_voicemails_json_contract(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _find_handler(app_instance, "/api/v1/telephone/voicemails", "GET")
        assert handler is not None
        request = MagicMock()
        request.query = _Query({"limit": "50", "offset": "0"})
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, TELEPHONE_VOICEMAILS_ENVELOPE_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_telephone_ringtones_list_json_contract(
    mock_rns_minimal, temp_dir
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _find_handler(app_instance, "/api/v1/telephone/ringtones", "GET")
        assert handler is not None
        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, TELEPHONE_RINGTONES_LIST_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_telephone_ringtones_status_json_contract(
    mock_rns_minimal, temp_dir
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _find_handler(
            app_instance, "/api/v1/telephone/ringtones/status", "GET"
        )
        assert handler is not None
        request = MagicMock()
        request.query = _Query({})
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, TELEPHONE_RINGTONE_STATUS_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_telephone_contacts_list_json_contract(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _find_handler(app_instance, "/api/v1/telephone/contacts", "GET")
        assert handler is not None
        request = MagicMock()
        request.query = _Query({"limit": "100", "offset": "0"})
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, TELEPHONE_CONTACTS_LIST_SCHEMA)


@pytest.mark.asyncio
async def test_api_v1_telephone_contacts_check_json_contract(
    mock_rns_minimal, temp_dir
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = _find_handler(
            app_instance,
            "/api/v1/telephone/contacts/check/{identity_hash}",
            "GET",
        )
        assert handler is not None
        request = MagicMock()
        request.match_info = {"identity_hash": "a1" * 16}
        response = await handler(request)
        data = json.loads(response.body)
        assert_matches_schema(data, TELEPHONE_CONTACT_CHECK_SCHEMA)
