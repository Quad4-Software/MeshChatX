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
        # Mock the new blackhole methods
        mock_rns_instance.blackhole_identity = MagicMock()
        mock_rns_instance.unblackhole_identity = MagicMock()
        mock_rns_instance.get_blackholed_identities.return_value = {}

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"\x00" * 32
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_banish_identity_with_blackhole(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Ensure blackhole integration is enabled
        app_instance.config.blackhole_integration_enabled.set(True)

        # Mock database
        app_instance.database = MagicMock()
        app_instance.database.announces.get_announce_by_hash.return_value = None

        target_hash = "a" * 32

        # Mock request
        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": target_hash})

        # Find handler
        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/blocked-destinations" and route.method == "POST":
                handler = route.handler
                break

        assert handler is not None

        response = await handler(request)
        assert response.status == 200

        # Verify DB call
        app_instance.database.misc.add_blocked_destination.assert_called_with(
            target_hash,
        )

        # Verify RNS blackhole call
        app_instance.reticulum.blackhole_identity.assert_called()
        args, kwargs = app_instance.reticulum.blackhole_identity.call_args
        assert args[0] == bytes.fromhex(target_hash)


@pytest.mark.asyncio
async def test_banish_identity_with_resolution(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        app_instance.config.blackhole_integration_enabled.set(True)
        app_instance.database = MagicMock()

        dest_hash = "d" * 32
        ident_hash = "e" * 32

        # Mock identity resolution
        app_instance.database.announces.get_announce_by_hash.return_value = {
            "identity_hash": ident_hash,
        }

        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": dest_hash})

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/blocked-destinations" and route.method == "POST":
                handler = route.handler
                break

        await handler(request)

        # Should have blackholed the IDENTITY hash, not the destination hash
        app_instance.reticulum.blackhole_identity.assert_called()
        args, _ = app_instance.reticulum.blackhole_identity.call_args
        assert args[0] == bytes.fromhex(ident_hash)


@pytest.mark.asyncio
async def test_banish_identity_disabled_integration(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # DISABLE blackhole integration
        app_instance.config.blackhole_integration_enabled.set(False)
        app_instance.database = MagicMock()

        target_hash = "b" * 32
        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": target_hash})

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/blocked-destinations" and route.method == "POST":
                handler = route.handler
                break

        await handler(request)

        # DB call should still happen
        app_instance.database.misc.add_blocked_destination.assert_called_with(
            target_hash,
        )

        # RNS blackhole call should NOT happen
        app_instance.reticulum.blackhole_identity.assert_not_called()


@pytest.mark.asyncio
async def test_lift_banishment(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        app_instance.config.blackhole_integration_enabled.set(True)
        app_instance.database = MagicMock()
        # Mock identity resolution
        app_instance.database.announces.get_announce_by_hash.return_value = None

        target_hash = "c" * 32

        # Mock request with match_info for the variable in path
        request = MagicMock()
        request.match_info = {"destination_hash": target_hash}

        handler = None
        for route in app_instance.get_routes():
            if (
                route.path == "/api/v1/blocked-destinations/{destination_hash}"
                and route.method == "DELETE"
            ):
                handler = route.handler
                break

        assert handler is not None

        await handler(request)

        # Verify DB call
        app_instance.database.misc.delete_blocked_destination.assert_called_with(
            target_hash,
        )

        # Verify RNS unblackhole call
        app_instance.reticulum.unblackhole_identity.assert_called()
        args, _ = app_instance.reticulum.unblackhole_identity.call_args
        assert args[0] == bytes.fromhex(target_hash)


@pytest.mark.asyncio
async def test_get_blackhole_list(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        ident_hash_bytes = b"\x01" * 32
        app_instance.reticulum.get_blackholed_identities.return_value = {
            ident_hash_bytes: {
                "source": b"\x02" * 32,
                "until": 1234567890,
                "reason": "Spam",
            },
        }

        request = MagicMock()

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/reticulum/blackhole" and route.method == "GET":
                handler = route.handler
                break

        assert handler is not None

        response = await handler(request)
        data = json.loads(response.body)

        assert ident_hash_bytes.hex() in data["blackholed_identities"]
        info = data["blackholed_identities"][ident_hash_bytes.hex()]
        assert info["reason"] == "Spam"
        assert info["source"] == (b"\x02" * 32).hex()
