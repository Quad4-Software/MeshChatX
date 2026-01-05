import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.rncp_handler import RNCPHandler


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    # Save real Identity class to use as base for our mock class
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with (
        patch("RNS.Reticulum") as mock_reticulum,
        patch("RNS.Transport") as mock_transport,
        patch("RNS.Identity", MockIdentityClass),
        patch("RNS.Destination") as mock_destination,
        patch("RNS.Resource") as mock_resource,
        patch("RNS.Link") as mock_link_class,
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
            mock_dest_instance = MagicMock()
            mock_destination.return_value = mock_dest_instance

            mock_link_instance = MagicMock()
            mock_link_class.return_value = mock_link_instance
            mock_link_instance.status = RNS.Link.ACTIVE

            mock_resource_instance = MagicMock()
            mock_resource_instance.status = 2  # COMPLETE
            mock_resource_instance.hash = b"res_hash"
            mock_resource.return_value = mock_resource_instance
            mock_resource.COMPLETE = 2
            mock_resource.FAILED = 3

            mock_transport.active_links = []
            mock_transport.has_path.return_value = True

            yield {
                "Reticulum": mock_reticulum,
                "Transport": mock_transport,
                "Identity": MockIdentityClass,
                "Destination": mock_destination,
                "Resource": mock_resource,
                "Link": mock_link_class,
                "link_instance": mock_link_instance,
                "id_instance": mock_id_instance,
                "dest_instance": mock_dest_instance,
            }


def test_rncp_handler_init(mock_rns, temp_dir):
    handler = RNCPHandler(mock_rns["Reticulum"], mock_rns["id_instance"], temp_dir)
    assert handler.reticulum == mock_rns["Reticulum"]
    assert handler.identity == mock_rns["id_instance"]
    assert handler.storage_dir == temp_dir


def test_setup_receive_destination(mock_rns, temp_dir):
    handler = RNCPHandler(mock_rns["Reticulum"], mock_rns["id_instance"], temp_dir)

    mock_rns["Reticulum"].identitypath = temp_dir
    _ = handler.setup_receive_destination(
        allowed_hashes=["abc123def456"],
        fetch_allowed=True,
        fetch_jail=temp_dir,
    )

    assert handler.receive_destination is not None
    mock_rns["Destination"].assert_called()
    assert handler.allowed_identity_hashes == [bytes.fromhex("abc123def456")]
    assert handler.fetch_jail == temp_dir


def test_receive_resource_callback(mock_rns, temp_dir):
    handler = RNCPHandler(mock_rns["Reticulum"], mock_rns["id_instance"], temp_dir)
    handler.allowed_identity_hashes = [b"allowed_hash"]

    mock_resource = MagicMock()
    mock_link = MagicMock()
    mock_remote_id = MagicMock()
    mock_remote_id.hash = b"allowed_hash"
    mock_link.get_remote_identity.return_value = mock_remote_id
    mock_resource.link = mock_link

    # Allowed
    assert handler._receive_resource_callback(mock_resource) is True

    # Not allowed
    mock_remote_id.hash = b"other_hash"
    assert handler._receive_resource_callback(mock_resource) is False


def test_receive_resource_concluded_success(mock_rns, temp_dir):
    handler = RNCPHandler(mock_rns["Reticulum"], mock_rns["id_instance"], temp_dir)

    mock_resource = MagicMock()
    mock_resource.status = RNS.Resource.COMPLETE
    mock_resource.hash = b"resource_hash"
    mock_resource.metadata = {"name": b"test_file.txt"}

    # Create dummy source file
    source_file = os.path.join(temp_dir, "temp_resource_data")
    with open(source_file, "w") as f:
        f.write("test data")
    mock_resource.data.name = source_file

    handler.active_transfers["7265736f757263655f68617368"] = {"status": "receiving"}

    handler._receive_resource_concluded(mock_resource)

    # Check if file was moved to rncp_received
    received_dir = os.path.join(temp_dir, "rncp_received")
    assert os.path.exists(os.path.join(received_dir, "test_file.txt"))
    assert (
        handler.active_transfers["7265736f757263655f68617368"]["status"] == "completed"
    )


@pytest.mark.asyncio
async def test_send_file_success(mock_rns, temp_dir):
    handler = RNCPHandler(mock_rns["Reticulum"], mock_rns["id_instance"], temp_dir)

    test_file = os.path.join(temp_dir, "send_me.txt")
    with open(test_file, "w") as f:
        f.write("payload")

    # Mocking the async behavior
    result = await handler.send_file(b"dest_hash", test_file, timeout=10)

    assert result["status"] == "completed"
    mock_rns["Link"].assert_called()
    mock_rns["Resource"].assert_called()
