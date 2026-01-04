import shutil
import tempfile
import base64
import secrets
from unittest.mock import MagicMock, patch, mock_open

import pytest
import RNS
from meshchatx.meshchat import ReticulumMeshChat, main


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    # Save the real identity class to use as base for our mock class
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("RNS.Transport") as mock_transport,
        patch("RNS.Identity", MockIdentityClass),
        patch("threading.Thread"),
        patch("LXMF.LXMRouter"),
        patch.object(ReticulumMeshChat, "announce_loop", return_value=None),
        patch.object(
            ReticulumMeshChat, "announce_sync_propagation_nodes", return_value=None
        ),
        patch.object(ReticulumMeshChat, "crawler_loop", return_value=None),
        patch.object(ReticulumMeshChat, "auto_backup_loop", return_value=None),
        patch.object(
            ReticulumMeshChat, "send_config_to_websocket_clients", return_value=None
        ),
    ):
        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(return_value=b"test_private_key")

        with (
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance),
            patch.object(
                MockIdentityClass, "from_bytes", return_value=mock_id_instance
            ),
        ):
            yield {
                "Reticulum": mock_reticulum,
                "Transport": mock_transport,
                "Identity": MockIdentityClass,
                "id_instance": mock_id_instance,
            }


# 1. Test HTTPS/HTTP and WS/WSS configuration logic
def test_run_https_logic(mock_rns, temp_dir):
    with (
        patch("meshchatx.src.backend.identity_context.Database"),
        patch(
            "meshchatx.src.backend.identity_context.ConfigManager"
        ) as mock_config_class,
        patch("meshchatx.meshchat.generate_ssl_certificate") as mock_gen_cert,
        patch("ssl.SSLContext") as mock_ssl_context,
        patch("aiohttp.web.run_app") as mock_run_app,
        # Mock all handlers to avoid RNS/LXMF calls
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
        mock_config = mock_config_class.return_value
        # provide a real-looking secret key
        mock_config.auth_session_secret.get.return_value = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode()
        mock_config.display_name.get.return_value = "Test"
        mock_config.lxmf_propagation_node_stamp_cost.get.return_value = 0
        mock_config.lxmf_delivery_transfer_limit_in_bytes.get.return_value = 1000000
        mock_config.lxmf_inbound_stamp_cost.get.return_value = 0
        mock_config.lxmf_preferred_propagation_node_destination_hash.get.return_value = None
        mock_config.lxmf_local_propagation_node_enabled.get.return_value = False
        mock_config.libretranslate_url.get.return_value = "http://localhost:5000"
        mock_config.translator_enabled.get.return_value = False
        mock_config.initial_docs_download_attempted.get.return_value = True

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Test HTTPS enabled
        app.run(host="127.0.0.1", port=8000, launch_browser=False, enable_https=True)
        mock_gen_cert.assert_called()
        mock_ssl_context.assert_called()
        # Verify run_app was called with ssl_context
        args, kwargs = mock_run_app.call_args
        assert "ssl_context" in kwargs
        assert kwargs["ssl_context"] is not None

        # Test HTTPS disabled
        mock_run_app.reset_mock()
        app.run(host="127.0.0.1", port=8000, launch_browser=False, enable_https=False)
        args, kwargs = mock_run_app.call_args
        assert kwargs.get("ssl_context") is None
        app.teardown_identity()


# 2. Test specific database integrity failure recovery
def test_database_integrity_recovery(mock_rns, temp_dir):
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
        patch("meshchatx.src.backend.identity_context.TelephoneManager"),
        patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        patch("meshchatx.src.backend.identity_context.RNCPHandler"),
        patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
    ):
        mock_db_instance = mock_db_class.return_value
        # Fail the first initialize call
        mock_db_instance.initialize.side_effect = [
            Exception("Database integrity failed"),
            None,
            None,
        ]

        # Mock integrity check and checkpoint
        mock_db_instance.provider.integrity_check.return_value = "ok"
        mock_db_instance.provider.checkpoint.return_value = True

        mock_config = mock_config_class.return_value
        mock_config.auth_session_secret.get.return_value = "test_secret"
        mock_config.display_name.get.return_value = "Test"

        app = ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
            auto_recover=True,
        )

        # Verify recovery steps were called in IdentityContext.setup() or app._run_startup_auto_recovery
        assert mock_db_instance.provider.checkpoint.called
        assert mock_db_instance.provider.integrity_check.called
        assert mock_db_instance.provider.vacuum.called
        assert mock_db_instance._tune_sqlite_pragmas.called
        app.teardown_identity()


# 3. Test missing critical files (identity)
def test_identity_loading_fallback(mock_rns, temp_dir):
    with (
        patch("meshchatx.src.backend.identity_context.Database"),
        patch(
            "meshchatx.src.backend.identity_context.ConfigManager"
        ) as mock_config_class,
        patch("RNS.Identity") as mock_id_class,
        patch("os.path.exists", return_value=False),  # Pretend files don't exist
        patch("builtins.open", mock_open()) as mock_file,
    ):
        mock_config = mock_config_class.return_value
        mock_config.auth_session_secret.get.return_value = "test_secret"

        # Setup mock for random generation
        mock_gen_id = MagicMock()
        mock_gen_id.hash.hex.return_value = "generated_hash"
        mock_gen_id.get_private_key.return_value = b"private_key"
        mock_id_class.side_effect = (
            lambda create_keys=False: mock_gen_id if create_keys else MagicMock()
        )

        # Mock sys.argv to use default behavior (random generation)
        with patch("sys.argv", ["meshchat.py", "--storage-dir", temp_dir]):
            with patch(
                "meshchatx.meshchat.ReticulumMeshChat"
            ):  # Mock ReticulumMeshChat to avoid full init
                with patch("aiohttp.web.run_app"):
                    main()

        # Verify identity was generated and saved
        assert mock_file.called
        # Check that it was called to write the private key
        mock_gen_id.get_private_key.assert_called()


# 4. Test flags/envs
def test_cli_flags_and_envs(mock_rns, temp_dir):
    with (
        patch("meshchatx.meshchat.ReticulumMeshChat") as mock_app_class,
        patch("RNS.Identity"),
        patch("aiohttp.web.run_app"),
        patch("os.makedirs"),
    ):
        # Test Env Vars
        env = {
            "MESHCHAT_HOST": "1.2.3.4",
            "MESHCHAT_PORT": "9000",
            "MESHCHAT_AUTO_RECOVER": "true",
            "MESHCHAT_AUTH": "1",
        }
        with patch.dict("os.environ", env):
            with patch("sys.argv", ["meshchat.py"]):
                main()

                # Verify ReticulumMeshChat was called with values from ENV
                args, kwargs = mock_app_class.call_args
                assert kwargs["auto_recover"] is True
                assert kwargs["auth_enabled"] is True

                # Verify run was called with host/port from ENV
                mock_app_instance = mock_app_class.return_value
                run_args, run_kwargs = mock_app_instance.run.call_args
                assert run_args[0] == "1.2.3.4"
                assert run_args[1] == 9000

        # Test CLI Flags (override Envs)
        mock_app_class.reset_mock()
        with patch.dict("os.environ", env):
            with patch(
                "sys.argv",
                ["meshchat.py", "--host", "5.6.7.8", "--port", "7000", "--no-https"],
            ):
                main()

                mock_app_instance = mock_app_class.return_value
                run_args, run_kwargs = mock_app_instance.run.call_args
                assert run_args[0] == "5.6.7.8"
                assert run_args[1] == 7000
                assert run_kwargs["enable_https"] is False
