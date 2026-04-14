from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.rncp_handler import RNCPHandler


@pytest.fixture
def mock_reticulum():
    return MagicMock()


@pytest.fixture
def mock_identity():
    return MagicMock()


@pytest.fixture
def rncp_handler(mock_reticulum, mock_identity, tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return RNCPHandler(mock_reticulum, mock_identity, str(storage_dir))


def test_rncp_handler_init(rncp_handler, mock_reticulum, mock_identity):
    assert rncp_handler.reticulum == mock_reticulum
    assert rncp_handler.identity == mock_identity
    assert rncp_handler.active_transfers == {}


@patch("meshchatx.src.backend.rncp_handler.RNS.Identity")
@patch("meshchatx.src.backend.rncp_handler.RNS.Destination")
@patch("meshchatx.src.backend.rncp_handler.RNS.Reticulum")
def test_setup_receive_destination(
    mock_rns_reticulum, mock_dest, mock_identity_class, rncp_handler,
):
    mock_rns_reticulum.identitypath = "/tmp/rns/identities"
    mock_id_obj = MagicMock()
    mock_identity_class.from_file.return_value = mock_id_obj
    mock_dest_obj = MagicMock()
    mock_dest_obj.hash = b"dest_hash"
    mock_dest.return_value = mock_dest_obj

    with patch("os.path.isfile", return_value=True):
        hash_hex = rncp_handler.setup_receive_destination(allowed_hashes=["abcd"])
        assert hash_hex == b"dest_hash".hex()
        assert bytes.fromhex("abcd") in rncp_handler.allowed_identity_hashes


def test_receive_sender_identified_allowed(rncp_handler):
    mock_link = MagicMock()
    mock_identity = MagicMock()
    mock_identity.hash = b"allowed"
    rncp_handler.allowed_identity_hashes = [b"allowed"]

    rncp_handler._receive_sender_identified(mock_link, mock_identity)
    mock_link.teardown.assert_not_called()


def test_receive_sender_identified_denied(rncp_handler):
    mock_link = MagicMock()
    mock_identity = MagicMock()
    mock_identity.hash = b"denied"
    rncp_handler.allowed_identity_hashes = [b"allowed"]

    rncp_handler._receive_sender_identified(mock_link, mock_identity)
    mock_link.teardown.assert_called_once()


def test_receive_resource_callback(rncp_handler):
    mock_resource = MagicMock()
    mock_resource.link.get_remote_identity.return_value.hash = b"allowed"
    rncp_handler.allowed_identity_hashes = [b"allowed"]

    assert rncp_handler._receive_resource_callback(mock_resource) is True

    mock_resource.link.get_remote_identity.return_value.hash = b"denied"
    assert rncp_handler._receive_resource_callback(mock_resource) is False


def test_receive_resource_started(rncp_handler):
    mock_resource = MagicMock()
    mock_resource.hash = b"res_hash"

    rncp_handler._receive_resource_started(mock_resource)
    assert b"res_hash".hex() in rncp_handler.active_transfers
    assert rncp_handler.active_transfers[b"res_hash".hex()]["status"] == "receiving"


def test_get_listener_status_not_listening(rncp_handler):
    s = rncp_handler.get_listener_status()
    assert s["listening"] is False
    assert s["destination_hash"] is None
    assert s["allowed_hashes"] == []


@patch("meshchatx.src.backend.rncp_handler.RNS.Transport")
@patch("meshchatx.src.backend.rncp_handler.RNS.Identity")
@patch("meshchatx.src.backend.rncp_handler.RNS.Destination")
@patch("meshchatx.src.backend.rncp_handler.RNS.Reticulum")
def test_teardown_receive_destination_deregisters(
    mock_rns_reticulum,
    mock_dest_class,
    mock_identity_class,
    mock_transport,
    rncp_handler,
):
    mock_rns_reticulum.identitypath = "/tmp/rns/identities"
    mock_id_obj = MagicMock()
    mock_identity_class.from_file.return_value = mock_id_obj
    mock_dest_obj = MagicMock()
    mock_dest_obj.hash = b"\x01" * 16
    mock_dest_class.return_value = mock_dest_obj

    with patch("os.path.isfile", return_value=True):
        rncp_handler.setup_receive_destination(allowed_hashes=["ab" * 16])

    rncp_handler.teardown_receive_destination()

    mock_transport.deregister_destination.assert_called_once_with(mock_dest_obj)
    assert rncp_handler.receive_destination is None


@patch("meshchatx.src.backend.rncp_handler.RNS.Transport")
@patch("meshchatx.src.backend.rncp_handler.RNS.Identity")
@patch("meshchatx.src.backend.rncp_handler.RNS.Destination")
@patch("meshchatx.src.backend.rncp_handler.RNS.Reticulum")
def test_setup_receive_destination_idempotent_restarts_listener(
    mock_rns_reticulum,
    mock_dest_class,
    mock_identity_class,
    mock_transport,
    rncp_handler,
):
    mock_rns_reticulum.identitypath = "/tmp/rns/identities"
    mock_id_obj = MagicMock()
    mock_identity_class.from_file.return_value = mock_id_obj
    first_dest = MagicMock()
    first_dest.hash = b"\x02" * 16
    second_dest = MagicMock()
    second_dest.hash = b"\x03" * 16
    mock_dest_class.side_effect = [first_dest, second_dest]

    with patch("os.path.isfile", return_value=True):
        rncp_handler.setup_receive_destination(allowed_hashes=["cd" * 16])
        rncp_handler.setup_receive_destination(allowed_hashes=["ef" * 16])

    assert mock_transport.deregister_destination.call_count == 1
    assert mock_transport.deregister_destination.call_args[0][0] is first_dest
    assert rncp_handler.receive_destination is second_dest
