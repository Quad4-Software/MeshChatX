from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.announce_manager import AnnounceManager


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.provider = MagicMock()
    db.announces = MagicMock()
    return db


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.announce_limit_lxmf_delivery = MagicMock()
    config.announce_limit_nomadnetwork_node = MagicMock()
    config.announce_limit_lxmf_propagation = MagicMock()
    return config


def test_announce_limit_rejects_when_at_capacity(mock_db, mock_config):
    mock_config.announce_limit_lxmf_delivery.get.return_value = 2
    mock_db.announces.get_announce_by_hash.return_value = None
    mock_db.announces.get_announce_count_by_aspect.return_value = 2

    manager = AnnounceManager(mock_db, mock_config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"new_dest", "lxmf.delivery", b"app_data", b"packet_hash"
    )

    mock_db.announces.upsert_announce.assert_not_called()


def test_announce_limit_allows_when_under_capacity(mock_db, mock_config):
    mock_config.announce_limit_lxmf_delivery.get.return_value = 10
    mock_db.announces.get_announce_by_hash.return_value = None
    mock_db.announces.get_announce_count_by_aspect.return_value = 5

    manager = AnnounceManager(mock_db, mock_config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"new_dest", "lxmf.delivery", b"app_data", b"packet_hash"
    )

    mock_db.announces.upsert_announce.assert_called_once()


def test_announce_limit_allows_update_of_existing(mock_db, mock_config):
    mock_config.announce_limit_lxmf_delivery.get.return_value = 1
    mock_db.announces.get_announce_by_hash.return_value = {
        "destination_hash": b"existing".hex(),
        "aspect": "lxmf.delivery",
    }
    mock_db.announces.get_announce_count_by_aspect.return_value = 1

    manager = AnnounceManager(mock_db, mock_config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"existing", "lxmf.delivery", b"app_data", b"packet_hash"
    )

    mock_db.announces.upsert_announce.assert_called_once()


def test_announce_limit_none_means_no_limit(mock_db, mock_config):
    mock_config.announce_limit_lxmf_delivery.get.return_value = None
    mock_db.announces.get_announce_by_hash.return_value = None
    mock_db.announces.get_announce_count_by_aspect.return_value = 1000

    manager = AnnounceManager(mock_db, mock_config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"new_dest", "lxmf.delivery", b"app_data", b"packet_hash"
    )

    mock_db.announces.upsert_announce.assert_called_once()


def test_announce_limit_nomadnetwork_aspect(mock_db, mock_config):
    mock_config.announce_limit_nomadnetwork_node.get.return_value = 1
    mock_db.announces.get_announce_by_hash.return_value = None
    mock_db.announces.get_announce_count_by_aspect.return_value = 1

    manager = AnnounceManager(mock_db, mock_config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"new_dest",
        "nomadnetwork.node",
        b"app_data",
        b"packet_hash",
    )

    mock_db.announces.upsert_announce.assert_not_called()


def test_announce_limit_propagation_aspect(mock_db, mock_config):
    mock_config.announce_limit_lxmf_propagation.get.return_value = 0
    mock_db.announces.get_announce_by_hash.return_value = None
    mock_db.announces.get_announce_count_by_aspect.return_value = 0

    manager = AnnounceManager(mock_db, mock_config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"new_dest",
        "lxmf.propagation",
        b"app_data",
        b"packet_hash",
    )

    mock_db.announces.upsert_announce.assert_not_called()


def test_announce_handles_none_packet_hash(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"dest", "lxmf.delivery", b"app_data", None
    )

    mock_db.announces.upsert_announce.assert_called_once()
    args, _ = mock_db.announces.upsert_announce.call_args
    assert args[0]["rssi"] is None
    assert args[0]["snr"] is None
