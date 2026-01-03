import os
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def mock_rns():
    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("RNS.Transport") as mock_transport,
        patch("RNS.Identity") as mock_identity,
        patch("threading.Thread"),
        patch.object(
            ReticulumMeshChat,
            "announce_loop",
            new=MagicMock(return_value=None),
        ),
        patch.object(
            ReticulumMeshChat,
            "announce_sync_propagation_nodes",
            new=MagicMock(return_value=None),
        ),
        patch.object(
            ReticulumMeshChat,
            "crawler_loop",
            new=MagicMock(return_value=None),
        ),
    ):
        # Setup mock identity
        mock_id_instance = MagicMock()
        # Use a real bytes object for hash so .hex() works naturally
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_private_key"
        mock_identity.return_value = mock_id_instance
        mock_identity.from_file.return_value = mock_id_instance

        # Setup mock transport
        mock_transport.interfaces = []
        mock_transport.destinations = []
        mock_transport.active_links = []
        mock_transport.announce_handlers = []

        yield {
            "Reticulum": mock_reticulum,
            "Transport": mock_transport,
            "Identity": mock_identity,
            "id_instance": mock_id_instance,
        }


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.mark.asyncio
async def test_cleanup_rns_state_for_identity(mock_rns, temp_dir):
    # Mock database and other managers to avoid heavy initialization
    with (
        patch("meshchatx.meshchat.Database"),
        patch("meshchatx.meshchat.ConfigManager"),
        patch("meshchatx.meshchat.MessageHandler"),
        patch("meshchatx.meshchat.AnnounceManager"),
        patch("meshchatx.meshchat.ArchiverManager"),
        patch("meshchatx.meshchat.MapManager"),
        patch("meshchatx.meshchat.TelephoneManager"),
        patch("meshchatx.meshchat.VoicemailManager"),
        patch("meshchatx.meshchat.RingtoneManager"),
        patch("meshchatx.meshchat.RNCPHandler"),
        patch("meshchatx.meshchat.RNStatusHandler"),
        patch("meshchatx.meshchat.RNProbeHandler"),
        patch("meshchatx.meshchat.TranslatorHandler"),
        patch("LXMF.LXMRouter"),
    ):
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Create a mock destination that should be cleaned up
        mock_dest = MagicMock()
        mock_dest.identity = mock_rns["id_instance"]
        mock_rns["Transport"].destinations = [mock_dest]

        # Create a mock link that should be cleaned up
        mock_link = MagicMock()
        mock_link.destination = mock_dest
        mock_rns["Transport"].active_links = [mock_link]

        app.cleanup_rns_state_for_identity(mock_rns["id_instance"].hash)

        # Verify deregistration and teardown were called
        mock_rns["Transport"].deregister_destination.assert_called_with(mock_dest)
        mock_link.teardown.assert_called()


@pytest.mark.asyncio
async def test_teardown_identity(mock_rns, temp_dir):
    with (
        patch("meshchatx.meshchat.Database"),
        patch("meshchatx.meshchat.ConfigManager"),
        patch("meshchatx.meshchat.MessageHandler"),
        patch("meshchatx.meshchat.AnnounceManager"),
        patch("meshchatx.meshchat.ArchiverManager"),
        patch("meshchatx.meshchat.MapManager"),
        patch("meshchatx.meshchat.TelephoneManager"),
        patch("meshchatx.meshchat.VoicemailManager"),
        patch("meshchatx.meshchat.RingtoneManager"),
        patch("meshchatx.meshchat.RNCPHandler"),
        patch("meshchatx.meshchat.RNStatusHandler"),
        patch("meshchatx.meshchat.RNProbeHandler"),
        patch("meshchatx.meshchat.TranslatorHandler"),
        patch("LXMF.LXMRouter"),
    ):
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Add some mock handlers to check deregistration
        mock_handler = MagicMock()
        mock_handler.aspect_filter = "test"
        mock_rns["Transport"].announce_handlers = [mock_handler]

        app.teardown_identity()

        assert app.running is False
        mock_rns["Transport"].deregister_announce_handler.assert_called_with(
            mock_handler,
        )
        app.database.close.assert_called()


@pytest.mark.asyncio
async def test_reload_reticulum(mock_rns, temp_dir):
    with (
        patch("meshchatx.meshchat.Database"),
        patch("meshchatx.meshchat.ConfigManager"),
        patch("meshchatx.meshchat.MessageHandler"),
        patch("meshchatx.meshchat.AnnounceManager"),
        patch("meshchatx.meshchat.ArchiverManager"),
        patch("meshchatx.meshchat.MapManager"),
        patch("meshchatx.meshchat.TelephoneManager"),
        patch("meshchatx.meshchat.VoicemailManager"),
        patch("meshchatx.meshchat.RingtoneManager"),
        patch("meshchatx.meshchat.RNCPHandler"),
        patch("meshchatx.meshchat.RNStatusHandler"),
        patch("meshchatx.meshchat.RNProbeHandler"),
        patch("meshchatx.meshchat.TranslatorHandler"),
        patch("LXMF.LXMRouter"),
        patch("asyncio.sleep", return_value=None),
        patch("socket.socket") as mock_socket,
    ):
        # Mock socket to simulate port 37429 becoming free immediately
        mock_sock_inst = MagicMock()
        mock_socket.return_value = mock_sock_inst

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Re-mock setup_identity to avoid multiple background thread starts during test
        app.setup_identity = MagicMock()

        result = await app.reload_reticulum()

        assert result is True
        mock_rns["Reticulum"].exit_handler.assert_called()
        # Verify RNS singleton was cleared (via private attribute access in code)
        assert mock_rns["Reticulum"]._Reticulum__instance is None
        # Verify setup_identity was called again
        app.setup_identity.assert_called()


@pytest.mark.asyncio
async def test_reload_reticulum_failure_recovery(mock_rns, temp_dir):
    with (
        patch("meshchatx.meshchat.Database"),
        patch("meshchatx.meshchat.ConfigManager"),
        patch("meshchatx.meshchat.MessageHandler"),
        patch("meshchatx.meshchat.AnnounceManager"),
        patch("meshchatx.meshchat.ArchiverManager"),
        patch("meshchatx.meshchat.MapManager"),
        patch("meshchatx.meshchat.TelephoneManager"),
        patch("meshchatx.meshchat.VoicemailManager"),
        patch("meshchatx.meshchat.RingtoneManager"),
        patch("meshchatx.meshchat.RNCPHandler"),
        patch("meshchatx.meshchat.RNStatusHandler"),
        patch("meshchatx.meshchat.RNProbeHandler"),
        patch("meshchatx.meshchat.TranslatorHandler"),
        patch("LXMF.LXMRouter"),
        patch("asyncio.sleep", return_value=None),
        patch("socket.socket"),
    ):
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Re-mock setup_identity to avoid multiple background thread starts and to check calls
        app.setup_identity = MagicMock()

        # Simulate a failure during reload AFTER reticulum was deleted
        if hasattr(app, "reticulum"):
            del app.reticulum

        # We need to make something else fail to reach the except block
        # or just mock a method inside the try block to raise.
        with patch.object(
            app,
            "teardown_identity",
            side_effect=Exception("Reload failed"),
        ):
            result = await app.reload_reticulum()

        assert result is False
        # Verify recovery: setup_identity should be called because hasattr(self, "reticulum") is False
        app.setup_identity.assert_called()


@pytest.mark.asyncio
async def test_hotswap_identity(mock_rns, temp_dir):
    with (
        patch("meshchatx.meshchat.Database"),
        patch("meshchatx.meshchat.ConfigManager"),
        patch("meshchatx.meshchat.MessageHandler"),
        patch("meshchatx.meshchat.AnnounceManager"),
        patch("meshchatx.meshchat.ArchiverManager"),
        patch("meshchatx.meshchat.MapManager"),
        patch("meshchatx.meshchat.TelephoneManager"),
        patch("meshchatx.meshchat.VoicemailManager"),
        patch("meshchatx.meshchat.RingtoneManager"),
        patch("meshchatx.meshchat.RNCPHandler"),
        patch("meshchatx.meshchat.RNStatusHandler"),
        patch("meshchatx.meshchat.RNProbeHandler"),
        patch("meshchatx.meshchat.TranslatorHandler"),
        patch("LXMF.LXMRouter"),
        patch("asyncio.sleep", return_value=None),
        patch("shutil.copy2"),
    ):
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Create a mock identity file for the new identity
        new_identity_hash = "new_hash"
        new_identity_dir = os.path.join(temp_dir, "identities", new_identity_hash)
        os.makedirs(new_identity_dir)
        with open(os.path.join(new_identity_dir, "identity"), "wb") as f:
            f.write(b"new_identity_data")

        app.reload_reticulum = AsyncMock(return_value=True)
        app.websocket_broadcast = AsyncMock()

        # Mock config to avoid JSON serialization error of MagicMocks
        app.config = MagicMock()
        app.config.display_name.get.return_value = "Test User"

        result = await app.hotswap_identity(new_identity_hash)

        assert result is True
        app.reload_reticulum.assert_called()
        app.websocket_broadcast.assert_called()
        # Check if the broadcast contains identity_switched
        broadcast_call = app.websocket_broadcast.call_args[0][0]
        assert "identity_switched" in broadcast_call
