import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


@pytest.fixture
def mock_app(temp_dir):
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
        patch("RNS.Identity") as mock_identity,
        patch("RNS.Reticulum"),
        patch("RNS.Transport"),
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
        mock_id = MagicMock()
        # Use a real bytes object for hash so .hex() works naturally
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.get_private_key.return_value = b"test_private_key"
        mock_identity.return_value = mock_id

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
