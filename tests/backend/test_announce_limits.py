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
    config.announce_max_stored_lxmf_delivery = MagicMock()
    config.announce_max_stored_nomadnetwork_node = MagicMock()
    config.announce_max_stored_lxmf_propagation = MagicMock()
    config.announce_fetch_limit_lxmf_delivery = MagicMock()
    config.announce_fetch_limit_nomadnetwork_node = MagicMock()
    config.announce_fetch_limit_lxmf_propagation = MagicMock()
    return config


def _make_manager(mock_db, mock_config):
    return AnnounceManager(mock_db, mock_config)


def test_trim_called_when_over_max_stored(mock_db, mock_config):
    mock_config.announce_max_stored_lxmf_delivery.get.return_value = 3

    manager = _make_manager(mock_db, mock_config)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"new_dest",
        "lxmf.delivery",
        b"app_data",
        b"packet_hash",
    )

    mock_db.announces.upsert_announce.assert_called_once()
    mock_db.announces.trim_announces_for_aspect.assert_called_once_with(
        "lxmf.delivery",
        3,
    )


def test_no_trim_without_config(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"dest",
        "lxmf.delivery",
        b"app_data",
        b"packet",
    )

    mock_db.announces.upsert_announce.assert_called_once()
    mock_db.announces.trim_announces_for_aspect.assert_not_called()


def test_max_stored_none_skips_trim(mock_db, mock_config):
    mock_config.announce_max_stored_lxmf_delivery.get.return_value = None

    manager = _make_manager(mock_db, mock_config)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"dest",
        "lxmf.delivery",
        b"app_data",
        b"packet",
    )

    mock_db.announces.trim_announces_for_aspect.assert_not_called()


def test_nomadnetwork_uses_own_max_key(mock_db, mock_config):
    mock_config.announce_max_stored_nomadnetwork_node.get.return_value = 5

    manager = _make_manager(mock_db, mock_config)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"dest",
        "nomadnetwork.node",
        b"app_data",
        b"packet",
    )

    mock_db.announces.trim_announces_for_aspect.assert_called_once_with(
        "nomadnetwork.node",
        5,
    )


def test_telephony_shares_lxmf_max(mock_db, mock_config):
    mock_config.announce_max_stored_lxmf_delivery.get.return_value = 7

    manager = _make_manager(mock_db, mock_config)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"dest",
        "lxst.telephony",
        b"app_data",
        b"packet",
    )

    mock_db.announces.trim_announces_for_aspect.assert_called_once_with(
        "lxst.telephony",
        7,
    )


def test_get_filtered_announces_resolves_default_limit(mock_db, mock_config):
    mock_config.announce_fetch_limit_lxmf_delivery.get.return_value = 33

    manager = _make_manager(mock_db, mock_config)
    manager.get_filtered_announces(aspect="lxmf.delivery", limit=None)

    args, _ = mock_db.provider.fetchall.call_args
    _sql, params = args
    assert 33 in params


def test_announce_handles_none_packet_hash(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"dest",
        "lxmf.delivery",
        b"app_data",
        None,
    )

    mock_db.announces.upsert_announce.assert_called_once()
    args, _ = mock_db.announces.upsert_announce.call_args
    assert args[0]["rssi"] is None
    assert args[0]["snr"] is None
