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
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("RNS.Transport"),
        patch("RNS.Identity") as mock_identity,
    ):
        mock_id_instance = MagicMock()
        mock_id_instance.hash = b"test_hash_32_bytes_long_01234567"
        mock_id_instance.get_private_key.return_value = b"test_key"
        mock_identity.return_value = mock_id_instance

        yield {"Reticulum": mock_reticulum, "id_instance": mock_id_instance}


def test_rns_config_auto_creation(mock_rns, temp_dir):
    """Test that Reticulum config is created if it does not exist."""
    config_dir = os.path.join(temp_dir, ".reticulum")
    config_file = os.path.join(config_dir, "config")

    # Ensure it doesn't exist
    assert not os.path.exists(config_file)

    with (
        patch("meshchatx.meshchat.IdentityContext"),
        patch("meshchatx.meshchat.WebAudioBridge"),
        patch("meshchatx.meshchat.memory_log_handler"),
    ):
        ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=config_dir,
        )

        # Method should have been called during init -> setup_identity
        assert os.path.exists(config_file)

        with open(config_file) as f:
            content = f.read()
            assert "[reticulum]" in content
            assert "[interfaces]" in content
            assert "enable_transport = False" in content


def test_rns_config_repair_if_invalid(mock_rns, temp_dir):
    """Test that Reticulum config is recreated if it is invalid/corrupt."""
    config_dir = os.path.join(temp_dir, ".reticulum")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "config")

    # Create a "corrupt" config
    with open(config_file, "w") as f:
        f.write("this is not a valid rns config")

    with (
        patch("meshchatx.meshchat.IdentityContext"),
        patch("meshchatx.meshchat.WebAudioBridge"),
        patch("meshchatx.meshchat.memory_log_handler"),
    ):
        ReticulumMeshChat(
            identity=mock_rns["id_instance"],
            storage_dir=temp_dir,
            reticulum_config_dir=config_dir,
        )

        with open(config_file) as f:
            content = f.read()
            # Should have been repaired
            assert "[reticulum]" in content
            assert "[interfaces]" in content
