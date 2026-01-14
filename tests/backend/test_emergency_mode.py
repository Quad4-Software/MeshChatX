import os
import shutil
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.database.provider import DatabaseProvider


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("RNS.Transport") as mock_transport,
        patch("RNS.Identity", MockIdentityClass),
        patch("threading.Thread") as mock_thread,
        patch("LXMF.LXMRouter") as mock_lxmf_router,
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(return_value=b"test_private_key")

        with (
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance),
            patch.object(
                MockIdentityClass,
                "from_bytes",
                return_value=mock_id_instance,
            ),
        ):
            mock_transport.interfaces = []
            mock_transport.destinations = []
            mock_transport.active_links = []
            mock_transport.announce_handlers = []

            mock_router_instance = MagicMock()
            mock_lxmf_router.return_value = mock_router_instance

            yield {
                "Reticulum": mock_reticulum,
                "Transport": mock_transport,
                "Identity": MockIdentityClass,
                "id_instance": mock_id_instance,
                "Thread": mock_thread,
                "LXMRouter": mock_lxmf_router,
                "router_instance": mock_router_instance,
            }


def test_emergency_mode_startup_logic(mock_rns, temp_dir):
    """Test that emergency mode flag is correctly passed and used."""
    with (
        patch("meshchatx.src.backend.identity_context.Database") as mock_db_class,
        patch("meshchatx.src.backend.identity_context.ConfigManager"),
        patch("meshchatx.src.backend.identity_context.MessageHandler"),
        patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        patch("meshchatx.src.backend.identity_context.MapManager"),
        patch("meshchatx.src.backend.identity_context.DocsManager"),
        patch("meshchatx.src.backend.identity_context.NomadNetworkManager"),
        patch(
            "meshchatx.src.backend.identity_context.TelephoneManager",
        ) as mock_tel_class,
        patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        patch("meshchatx.src.backend.identity_context.RNCPHandler"),
        patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
        patch(
            "meshchatx.src.backend.identity_context.IntegrityManager",
        ) as mock_integrity_class,
        patch(
            "meshchatx.src.backend.identity_context.IdentityContext.start_background_threads",
        ),
    ):
        # Initialize app in emergency mode
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            emergency=True,
        )

        assert app.emergency is True

        # Verify Database was initialized with :memory:
        mock_db_class.assert_called_with(":memory:")

        # Verify IntegrityManager.check_integrity was NOT called
        mock_integrity_instance = mock_integrity_class.return_value
        assert mock_integrity_instance.check_integrity.call_count == 0

        # Verify migrate_from_legacy was NOT called
        mock_db_instance = mock_db_class.return_value
        assert mock_db_instance.migrate_from_legacy.call_count == 0

        # Verify TelephoneManager.init_telephone was NOT called
        mock_tel_instance = mock_tel_class.return_value
        assert mock_tel_instance.init_telephone.call_count == 0

        # Verify IntegrityManager.save_manifest was NOT called
        assert mock_integrity_instance.save_manifest.call_count == 0


def test_emergency_mode_env_var(mock_rns, temp_dir):
    """Test that emergency mode can be engaged via environment variable."""
    with (
        patch.dict(os.environ, {"MESHCHAT_EMERGENCY": "1"}),
        patch("meshchatx.src.backend.identity_context.Database"),
        patch("meshchatx.src.backend.identity_context.ConfigManager"),
        patch("meshchatx.src.backend.identity_context.MessageHandler"),
        patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        patch("meshchatx.src.backend.identity_context.MapManager"),
        patch("meshchatx.src.backend.identity_context.DocsManager"),
        patch("meshchatx.src.backend.identity_context.NomadNetworkManager"),
        patch("meshchatx.src.backend.identity_context.TelephoneManager"),
        patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        patch("meshchatx.src.backend.identity_context.RNCPHandler"),
        patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
        patch(
            "meshchatx.src.backend.identity_context.IdentityContext.start_background_threads",
        ),
    ):
        # We need to simulate the argparse processing that happens in main()
        # but since we are testing ReticulumMeshChat directly, we check if it respects the flag
        from meshchatx.meshchat import env_bool

        is_emergency = env_bool("MESHCHAT_EMERGENCY", False)

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            emergency=is_emergency,
        )

        assert app.emergency is True


def test_normal_mode_startup_logic(mock_rns, temp_dir):
    """Verify that normal mode (non-emergency) still works as expected."""
    with (
        patch("meshchatx.src.backend.identity_context.Database") as mock_db_class,
        patch("meshchatx.src.backend.identity_context.ConfigManager"),
        patch("meshchatx.src.backend.identity_context.MessageHandler"),
        patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        patch("meshchatx.src.backend.identity_context.MapManager"),
        patch("meshchatx.src.backend.identity_context.DocsManager"),
        patch("meshchatx.src.backend.identity_context.NomadNetworkManager"),
        patch(
            "meshchatx.src.backend.identity_context.TelephoneManager",
        ) as mock_tel_class,
        patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        patch("meshchatx.src.backend.identity_context.RNCPHandler"),
        patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
        patch(
            "meshchatx.src.backend.identity_context.IntegrityManager",
        ) as mock_integrity_class,
        patch(
            "meshchatx.src.backend.identity_context.IdentityContext.start_background_threads",
        ),
    ):
        # Configure mocks BEFORE instantiating app
        mock_integrity_instance = mock_integrity_class.return_value
        mock_integrity_instance.check_integrity.return_value = (True, [])

        # Initialize app in normal mode (default)
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            emergency=False,
        )

        assert app.emergency is False

        # Verify Database was initialized with a real file path (not :memory:)
        db_path_arg = mock_db_class.call_args[0][0]
        assert db_path_arg != ":memory:"
        assert db_path_arg.endswith("database.db")

        # Verify IntegrityManager.check_integrity WAS called
        assert mock_integrity_instance.check_integrity.call_count == 1

        # Verify migrate_from_legacy WAS called
        mock_db_instance = mock_db_class.return_value
        assert mock_db_instance.migrate_from_legacy.call_count == 1

        # Verify TelephoneManager.init_telephone WAS called
        mock_tel_instance = mock_tel_class.return_value
        assert mock_tel_instance.init_telephone.call_count == 1

        # Verify IntegrityManager.save_manifest WAS called
        assert mock_integrity_instance.save_manifest.call_count == 1


def test_emergency_mode_memory_concurrency(mock_rns, temp_dir):
    """Verify that :memory: database connection is shared across threads."""
    # Reset singleton
    DatabaseProvider._instance = None

    with (
        patch(
            "meshchatx.src.backend.identity_context.IdentityContext.start_background_threads",
        ),
        patch("meshchatx.src.backend.identity_context.create_lxmf_router"),
        patch("meshchatx.meshchat.WebAudioBridge"),
        patch("meshchatx.meshchat.memory_log_handler"),
    ):
        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            emergency=True,
        )

        ctx = app.current_context
        provider = ctx.database.provider
        assert provider.db_path == ":memory:"

        # Set value in main thread
        test_name = "Emergency Worker"
        ctx.config.display_name.set(test_name)

        # Simulate another thread by swapping thread-local storage
        original_local = provider._local
        provider._local = threading.local()

        try:
            # Should still return the SAME connection object because of the fix
            val = ctx.config.display_name.get()
            assert val == test_name
        finally:
            provider._local = original_local

    DatabaseProvider._instance = None
