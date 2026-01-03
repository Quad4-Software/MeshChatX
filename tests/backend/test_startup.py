import os
import shutil
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest
import RNS
import LXMF

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    # Save real Identity class to use as base class for our mock class
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
        # Setup mock instance
        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(return_value=b"test_private_key")

        # We also need to mock the class methods on MockIdentityClass
        with (
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance),
            patch.object(
                MockIdentityClass, "from_bytes", return_value=mock_id_instance
            ),
        ):
            # Setup mock transport
            mock_transport.interfaces = []
            mock_transport.destinations = []
            mock_transport.active_links = []
            mock_transport.announce_handlers = []

            # Setup mock LXMF Router
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


def test_reticulum_meshchat_init(mock_rns, temp_dir):
    # Mocking all manager classes to avoid their complex initializations if possible,
    # but the user wanted "startup tests", so let's keep some real if they don't depend on too much.
    # Database initialization is important.

    with (
        patch("meshchatx.src.backend.identity_context.Database") as mock_db_class,
        patch(
            "meshchatx.src.backend.identity_context.ConfigManager"
        ) as mock_config_class,
        patch("meshchatx.src.backend.identity_context.MessageHandler"),
        patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        patch("meshchatx.src.backend.identity_context.MapManager"),
        patch("meshchatx.src.backend.identity_context.DocsManager"),
        patch("meshchatx.src.backend.identity_context.NomadNetworkManager"),
        patch(
            "meshchatx.src.backend.identity_context.TelephoneManager"
        ) as mock_tel_class,
        patch(
            "meshchatx.src.backend.identity_context.VoicemailManager"
        ) as mock_vm_class,
        patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        patch("meshchatx.src.backend.identity_context.RNCPHandler"),
        patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
    ):
        mock_db_instance = mock_db_class.return_value
        mock_config_instance = mock_config_class.return_value

        # Setup config mock values
        mock_config_instance.auth_enabled.get.return_value = False
        mock_config_instance.lxmf_propagation_node_stamp_cost.get.return_value = 0
        mock_config_instance.lxmf_delivery_transfer_limit_in_bytes.get.return_value = (
            1000000
        )
        mock_config_instance.lxmf_inbound_stamp_cost.get.return_value = 0
        mock_config_instance.display_name.get.return_value = "Test User"
        mock_config_instance.lxmf_preferred_propagation_node_destination_hash.get.return_value = None
        mock_config_instance.lxmf_local_propagation_node_enabled.get.return_value = (
            False
        )
        mock_config_instance.libretranslate_url.get.return_value = (
            "http://localhost:5000"
        )
        mock_config_instance.translator_enabled.get.return_value = False
        mock_config_instance.initial_docs_download_attempted.get.return_value = True

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Verify basic properties
        assert app.running is True
        assert app.storage_dir == temp_dir
        assert app.reticulum_config_dir == temp_dir

        # Verify database initialization
        mock_db_instance.initialize.assert_called_once()
        mock_db_instance.migrate_from_legacy.assert_called_once()

        # Verify RNS initialization
        mock_rns["Reticulum"].assert_called_once_with(temp_dir)

        # Verify LXMF Router initialization
        mock_rns["LXMRouter"].assert_called_once()

        # Verify Announce Handlers registration
        assert mock_rns["Transport"].register_announce_handler.call_count == 4

        # Verify background threads were started
        # There should be at least 3 threads: announce_loop, announce_sync_propagation_nodes, crawler_loop
        assert mock_rns["Thread"].call_count >= 3


def test_reticulum_meshchat_init_with_auth(mock_rns, temp_dir):
    with (
        patch("meshchatx.src.backend.identity_context.Database"),
        patch(
            "meshchatx.src.backend.identity_context.ConfigManager"
        ) as mock_config_class,
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
    ):
        mock_config_instance = mock_config_class.return_value
        mock_config_instance.auth_enabled.get.return_value = True

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            auth_enabled=True,
        )

        assert app.auth_enabled is True


def test_reticulum_meshchat_init_database_failure_recovery(mock_rns, temp_dir):
    with (
        patch("meshchatx.src.backend.identity_context.Database") as mock_db_class,
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
        patch.object(ReticulumMeshChat, "_run_startup_auto_recovery") as mock_recovery,
    ):
        mock_db_instance = mock_db_class.return_value
        # Fail the first initialize call
        mock_db_instance.initialize.side_effect = [Exception("DB Error"), None]

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            auto_recover=True,
        )

        assert mock_recovery.called
        assert mock_db_instance.initialize.call_count == 2
