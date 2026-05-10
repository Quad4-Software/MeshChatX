# SPDX-License-Identifier: 0BSD

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
    for _k in (
        "announce_store_lxmf_delivery",
        "announce_store_lxst_telephony",
        "announce_store_nomadnetwork_node",
        "announce_store_lxmf_propagation",
        "announce_store_git_repositories",
    ):
        _m = MagicMock()
        _m.get.return_value = True
        setattr(config, _k, _m)
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


def test_max_stored_clamps_to_one_million(mock_db, mock_config):
    mock_config.announce_max_stored_lxmf_delivery.get.return_value = 9_999_999

    manager = _make_manager(mock_db, mock_config)

    assert manager._get_max_stored_for_aspect("lxmf.delivery") == 1_000_000


def test_trim_called_with_clamped_max_stored(mock_db, mock_config):
    mock_config.announce_max_stored_lxmf_delivery.get.return_value = 5_000_000

    manager = _make_manager(mock_db, mock_config)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "ab" * 16
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"\x01" * 16,
        "lxmf.delivery",
        b"app_data",
        b"packet_hash",
    )

    mock_db.announces.trim_announces_for_aspect.assert_called_once_with(
        "lxmf.delivery",
        1_000_000,
    )


def test_max_stored_zero_skips_cap(mock_db, mock_config):
    mock_config.announce_max_stored_lxmf_delivery.get.return_value = 0

    manager = _make_manager(mock_db, mock_config)

    assert manager._get_max_stored_for_aspect("lxmf.delivery") is None


def test_fetch_limit_clamps_to_hundred_thousand(mock_db, mock_config):
    mock_config.announce_fetch_limit_lxmf_delivery = MagicMock()
    mock_config.announce_fetch_limit_lxmf_delivery.get.return_value = 800_000

    manager = _make_manager(mock_db, mock_config)

    assert manager._get_fetch_limit_for_aspect("lxmf.delivery") == 100_000


def test_fetch_limit_invalid_falls_back_to_default(mock_db, mock_config):
    mock_config.announce_fetch_limit_lxmf_delivery = MagicMock()
    mock_config.announce_fetch_limit_lxmf_delivery.get.return_value = 0

    manager = _make_manager(mock_db, mock_config)

    assert manager._get_fetch_limit_for_aspect("lxmf.delivery") == 2500


def test_fetch_limit_unknown_aspect_returns_default(mock_db, mock_config):
    manager = _make_manager(mock_db, mock_config)

    assert manager._get_fetch_limit_for_aspect("unknown.aspect") == 2500


def test_fetch_limit_none_falls_back_to_default(mock_db, mock_config):
    mock_config.announce_fetch_limit_lxmf_delivery = MagicMock()
    mock_config.announce_fetch_limit_lxmf_delivery.get.return_value = None

    manager = _make_manager(mock_db, mock_config)

    assert manager._get_fetch_limit_for_aspect("lxmf.delivery") == 2500


def test_get_filtered_announces_uses_clamped_fetch_limit(mock_db, mock_config):
    mock_config.announce_fetch_limit_lxmf_delivery = MagicMock()
    mock_config.announce_fetch_limit_lxmf_delivery.get.return_value = 400_000

    manager = _make_manager(mock_db, mock_config)
    manager.get_filtered_announces(aspect="lxmf.delivery", limit=None)

    args, _ = mock_db.provider.fetchall.call_args
    _sql, params = args
    assert 100_000 in params


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
