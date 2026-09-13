# SPDX-License-Identifier: 0BSD

import shutil
import tempfile
from unittest.mock import MagicMock, patch

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

        def get_private_key(self):
            return b"test_private_key"

        def load(self, *args, **kwargs):
            pass

        def load_private_key(self, *args, **kwargs):
            pass

    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("RNS.Transport") as mock_transport,
        patch("RNS.Identity", MockIdentityClass),
        patch("threading.Thread"),
        patch("LXMF.LXMRouter"),
        patch.object(ReticulumMeshChat, "announce_loop", return_value=None),
        patch.object(
            ReticulumMeshChat,
            "announce_sync_propagation_nodes",
            return_value=None,
        ),
        patch.object(ReticulumMeshChat, "crawler_loop", return_value=None),
        patch.object(ReticulumMeshChat, "auto_backup_loop", return_value=None),
        patch.object(
            ReticulumMeshChat,
            "send_config_to_websocket_clients",
            return_value=None,
        ),
    ):
        mock_id_instance = MockIdentityClass()

        with (
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance),
            patch.object(
                MockIdentityClass,
                "from_bytes",
                return_value=mock_id_instance,
            ),
        ):
            yield {
                "Reticulum": mock_reticulum,
                "Transport": mock_transport,
                "Identity": MockIdentityClass,
                "id_instance": mock_id_instance,
            }


def _ok_results():
    from meshchatx.src.backend.self_check import SELF_CHECK_LABELS

    return {key: {"status": "ok", "reason": ""} for key in SELF_CHECK_LABELS}


def test_self_check_cli_success(mock_rns, temp_dir):
    """Test that self-check CLI argument prints results and exits with 0 on success."""
    mock_results = _ok_results()

    with (
        patch("meshchatx.meshchat.ReticulumMeshChat") as mock_app_class,
        patch("meshchatx.src.backend.identity_context.core.Database"),
        patch("meshchatx.src.backend.identity_context.core.ConfigManager"),
        patch("aiohttp.web.run_app"),
        patch("sys.argv", ["meshchat.py", "--storage-dir", temp_dir, "--self-check"]),
    ):
        mock_app_instance = mock_app_class.return_value
        mock_app_instance.run_self_test = MagicMock(return_value=mock_results)

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 0
        mock_app_instance.run_self_test.assert_called_once()


def test_self_check_cli_failure(mock_rns, temp_dir):
    """Test that self-check CLI argument prints results and exits with 1 on failure."""
    mock_results = _ok_results()
    mock_results["stack_up"] = {
        "status": "failed",
        "reason": "Reticulum stack is not initialized",
    }
    mock_results["db_good"] = {
        "status": "failed",
        "reason": "Database check failed",
    }

    with (
        patch("meshchatx.meshchat.ReticulumMeshChat") as mock_app_class,
        patch("meshchatx.src.backend.identity_context.core.Database"),
        patch("meshchatx.src.backend.identity_context.core.ConfigManager"),
        patch("aiohttp.web.run_app"),
        patch("sys.argv", ["meshchat.py", "--storage-dir", temp_dir, "--self-check"]),
    ):
        mock_app_instance = mock_app_class.return_value
        mock_app_instance.run_self_test = MagicMock(return_value=mock_results)

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        mock_app_instance.run_self_test.assert_called_once()


def test_self_check_env_var_success(mock_rns, temp_dir):
    """Test that MESHCHAT_SELF_CHECK env var triggers self-check and exits with 0 on success."""
    mock_results = _ok_results()

    env = {
        "MESHCHAT_SELF_CHECK": "true",
        "MESHCHAT_STORAGE_DIR": temp_dir,
    }

    with (
        patch("meshchatx.meshchat.ReticulumMeshChat") as mock_app_class,
        patch("meshchatx.src.backend.identity_context.core.Database"),
        patch("meshchatx.src.backend.identity_context.core.ConfigManager"),
        patch("aiohttp.web.run_app"),
        patch.dict("os.environ", env),
        patch("sys.argv", ["meshchat.py"]),
    ):
        mock_app_instance = mock_app_class.return_value
        mock_app_instance.run_self_test = MagicMock(return_value=mock_results)

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 0
        mock_app_instance.run_self_test.assert_called_once()
