# SPDX-License-Identifier: 0BSD

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
async def test_favourites_import(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if route.path == "/api/v1/favourites/import" and route.method == "POST":
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "favourites": [
                    {
                        "destination_hash": "a" * 32,
                        "display_name": "Node A",
                        "aspect": "nomadnetwork.node",
                    },
                    {
                        "destination_hash": "b" * 32,
                        "display_name": "Node B",
                        "aspect": "nomadnetwork.node",
                    },
                ],
            },
        )
        response = await handler(request)
        data = json.loads(response.body)
        assert data["imported"] == 2
        assert data["skipped"] == 0

        rows = app.database.announces.get_favourites(aspect="nomadnetwork.node")
        assert len(rows) == 2


@pytest.mark.asyncio
async def test_favourites_import_skips_invalid(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if route.path == "/api/v1/favourites/import" and route.method == "POST":
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "favourites": [
                    {
                        "destination_hash": "a" * 32,
                        "display_name": "Node A",
                        "aspect": "nomadnetwork.node",
                    },
                    {"display_name": "Missing hash"},
                    {"destination_hash": "b" * 32, "aspect": None},
                ],
            },
        )
        response = await handler(request)
        data = json.loads(response.body)
        assert data["imported"] == 1
        assert data["skipped"] == 2


@pytest.mark.asyncio
async def test_favourites_import_deduplicates(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if route.path == "/api/v1/favourites/import" and route.method == "POST":
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "favourites": [
                    {
                        "destination_hash": "a" * 32,
                        "display_name": "First",
                        "aspect": "nomadnetwork.node",
                    },
                    {
                        "destination_hash": "a" * 32,
                        "display_name": "Second",
                        "aspect": "nomadnetwork.node",
                    },
                    {
                        "destination_hash": "b" * 32,
                        "display_name": "Node B",
                        "aspect": "nomadnetwork.node",
                    },
                ],
            },
        )
        response = await handler(request)
        data = json.loads(response.body)
        assert data["imported"] == 2
        assert data["skipped"] == 0

        rows = app.database.announces.get_favourites(aspect="nomadnetwork.node")
        assert len(rows) == 2
        names = {r["display_name"] for r in rows}
        assert names == {"Second", "Node B"}


@pytest.mark.asyncio
async def test_favourites_import_rejects_non_array(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        handler = None
        for route in app.get_routes():
            if route.path == "/api/v1/favourites/import" and route.method == "POST":
                handler = route.handler
                break
        assert handler is not None

        request = MagicMock()
        request.json = AsyncMock(return_value={"favourites": "not an array"})
        response = await handler(request)
        assert response.status == 400
