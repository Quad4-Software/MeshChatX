import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_contacts_export_empty(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/telephone/contacts/export"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert "contacts" in data
        assert data["contacts"] == []


@pytest.mark.asyncio
async def test_contacts_export_with_data(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app.database.contacts.add_contact("Alice", "a" * 32, lxmf_address="b" * 32)
        app.database.contacts.add_contact("Bob", "c" * 32)

        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/telephone/contacts/export"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        response = await handler(request)
        data = json.loads(response.body)
        assert "contacts" in data
        assert len(data["contacts"]) == 2
        names = {c["name"] for c in data["contacts"]}
        assert names == {"Alice", "Bob"}
        for c in data["contacts"]:
            assert "id" not in c
            assert "created_at" not in c
            assert "updated_at" not in c


@pytest.mark.asyncio
async def test_contacts_import_valid(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/telephone/contacts/import"
                and route.method == "POST"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "contacts": [
                    {"name": "Imported1", "remote_identity_hash": "d" * 32},
                    {
                        "name": "Imported2",
                        "remote_identity_hash": "e" * 32,
                        "lxmf_address": "f" * 32,
                    },
                ]
            }
        )
        response = await handler(request)
        data = json.loads(response.body)
        assert data["added"] == 2
        assert data["skipped"] == 0

        rows = app.database.contacts.get_contacts(limit=10)
        assert len(rows) == 2


@pytest.mark.asyncio
async def test_contacts_import_skips_invalid(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/telephone/contacts/import"
                and route.method == "POST"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "contacts": [
                    {"name": "Valid", "remote_identity_hash": "a" * 32},
                    {"name": ""},
                    {"remote_identity_hash": "b" * 32},
                ]
            }
        )
        response = await handler(request)
        data = json.loads(response.body)
        assert data["added"] == 1
        assert data["skipped"] == 2


@pytest.mark.asyncio
async def test_contacts_import_rejects_non_array(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/telephone/contacts/import"
                and route.method == "POST"
            ):
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(return_value={"contacts": "not an array"})
        response = await handler(request)
        assert response.status == 400
