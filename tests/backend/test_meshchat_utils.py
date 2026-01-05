import os
import shutil
import tempfile
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


@pytest.fixture
def mock_app(temp_dir):
    # Save real Identity class to use as base for our mock class
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        stack.enter_context(patch("meshchatx.src.backend.identity_context.Database"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ConfigManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.MessageHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.AnnounceManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ArchiverManager"),
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.MapManager"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TelephoneManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.VoicemailManager"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RingtoneManager"),
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.RNCPHandler"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TranslatorHandler"),
        )
        stack.enter_context(patch("LXMF.LXMRouter"))
        stack.enter_context(patch("RNS.Identity", MockIdentityClass))
        stack.enter_context(patch("RNS.Reticulum"))
        stack.enter_context(patch("RNS.Transport"))
        stack.enter_context(patch("threading.Thread"))
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_loop",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_sync_propagation_nodes",
                new=MagicMock(return_value=None),
            ),
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "crawler_loop",
                new=MagicMock(return_value=None),
            ),
        )

        mock_id = MockIdentityClass()
        mock_id.get_private_key = MagicMock(return_value=b"test_private_key")

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "from_bytes", return_value=mock_id),
        )

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        return app


def test_get_interfaces_snapshot(mock_app):
    # Setup mock reticulum config
    mock_reticulum = MagicMock()
    mock_reticulum.config = {
        "interfaces": {
            "Iface1": {"type": "TCP", "enabled": "yes"},
            "Iface2": {"type": "RNode", "enabled": "no"},
        },
    }
    mock_app.reticulum = mock_reticulum

    snapshot = mock_app._get_interfaces_snapshot()

    assert len(snapshot) == 2
    assert snapshot["Iface1"]["type"] == "TCP"
    assert snapshot["Iface2"]["enabled"] == "no"
    # Ensure it's a deep copy (not the same object)
    assert snapshot["Iface1"] is not mock_reticulum.config["interfaces"]["Iface1"]


def test_write_reticulum_config_success(mock_app):
    mock_reticulum = MagicMock()
    mock_app.reticulum = mock_reticulum

    result = mock_app._write_reticulum_config()

    assert result is True
    mock_reticulum.config.write.assert_called_once()


def test_write_reticulum_config_no_reticulum(mock_app):
    if hasattr(mock_app, "reticulum"):
        del mock_app.reticulum

    result = mock_app._write_reticulum_config()
    assert result is False


def test_write_reticulum_config_failure(mock_app):
    mock_reticulum = MagicMock()
    mock_reticulum.config.write.side_effect = Exception("Write failed")
    mock_app.reticulum = mock_reticulum

    result = mock_app._write_reticulum_config()
    assert result is False
