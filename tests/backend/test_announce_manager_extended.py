# SPDX-License-Identifier: 0BSD

import base64
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.announce_manager import AnnounceManager


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.provider = MagicMock()
    db.announces = MagicMock()
    return db


def test_upsert_announce(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    reticulum.get_packet_q.return_value = 3

    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum,
        identity,
        b"dest_hash",
        "aspect",
        b"app_data",
        b"packet_hash",
    )

    mock_db.announces.upsert_announce.assert_called_once()
    args, _ = mock_db.announces.upsert_announce.call_args
    data = args[0]
    assert data["destination_hash"] == b"dest_hash".hex()
    assert data["rssi"] == -50
    assert data["app_data"] == base64.b64encode(b"app_data").decode("utf-8")


def test_upsert_skips_when_store_disabled_for_aspect(mock_db):
    config = MagicMock()
    config.announce_store_lxmf_delivery = MagicMock()
    config.announce_store_lxmf_delivery.get.return_value = False
    manager = AnnounceManager(mock_db, config=config)
    manager.upsert_announce(
        None,
        MagicMock(),
        b"\x00" * 16,
        "lxmf.delivery",
        b"x",
        None,
    )
    mock_db.announces.upsert_announce.assert_not_called()


def test_is_storing_announce_for_aspect_respects_config(mock_db):
    config = MagicMock()
    config.announce_store_lxmf_propagation = MagicMock()
    config.announce_store_lxmf_propagation.get.return_value = False
    manager = AnnounceManager(mock_db, config=config)
    assert manager.is_storing_announce_for_aspect("lxmf.propagation") is False
    assert (
        manager.is_storing_announce_for_aspect("lxmf.propagation", force_store=True)
        is True
    )
    assert manager.is_storing_announce_for_aspect("unknown.aspect") is True


def test_upsert_force_store_bypasses_disabled_config(mock_db):
    config = MagicMock()
    config.announce_store_nomadnetwork_node = MagicMock()
    config.announce_store_nomadnetwork_node.get.return_value = False
    config.announce_max_stored_nomadnetwork_node = MagicMock()
    config.announce_max_stored_nomadnetwork_node.get.return_value = 1000
    manager = AnnounceManager(mock_db, config=config)
    idm = MagicMock()
    idm.hash.hex.return_value = "a" * 64
    idm.get_public_key.return_value = b"k"
    manager.upsert_announce(
        None,
        idm,
        b"\x00" * 16,
        "nomadnetwork.node",
        None,
        None,
        force_store=True,
    )
    mock_db.announces.upsert_announce.assert_called_once()


def test_get_filtered_announces(mock_db):
    manager = AnnounceManager(mock_db)
    manager.get_filtered_announces(aspect="test", query="search", limit=10)

    args, _ = mock_db.provider.fetchall.call_args
    sql, params = args
    assert "a.aspect = ?" in sql
    assert "(a.destination_hash LIKE ? OR a.identity_hash LIKE ?)" in sql
    assert "LIMIT ? OFFSET ?" in sql
    assert "test" in params
    assert "%search%" in params


def test_get_filtered_announces_count(mock_db):
    manager = AnnounceManager(mock_db)
    mock_db.provider.fetchone.return_value = {"count": 5}
    count = manager.get_filtered_announces_count(
        aspect="test",
        query="q",
        blocked_identity_hashes=["b1"],
    )
    assert count == 5

    args, _ = mock_db.provider.fetchone.call_args
    sql, params = args
    assert "SELECT COUNT(*)" in sql
    assert "a.aspect = ?" in sql
    assert "a.identity_hash NOT IN (?)" in sql
    assert "test" in params
    assert "b1" in params


def test_get_filtered_announces_all_fields(mock_db):
    manager = AnnounceManager(mock_db)
    manager.get_filtered_announces(
        aspect="a",
        identity_hash="ih",
        destination_hash="dh",
        query="q",
        blocked_identity_hashes=["b1", "b2"],
        limit=10,
        offset=20,
    )

    args, _ = mock_db.provider.fetchall.call_args
    sql, params = args
    assert "a.aspect = ?" in sql
    assert "a.identity_hash = ?" in sql
    assert "a.destination_hash = ?" in sql
    assert "a.identity_hash NOT IN (?, ?)" in sql
    assert 10 in params
    assert 20 in params


def test_get_announces_for_destination_hashes_chunks_and_filters(mock_db):
    manager = AnnounceManager(mock_db)
    mock_db.provider.fetchall.side_effect = [
        [{"destination_hash": "aa", "aspect": "lxmf.delivery"}],
        [{"destination_hash": "bb", "aspect": "nomadnetwork.node"}],
    ]
    hashes = ["AA", "bb", "aa"]
    out = manager.get_announces_for_destination_hashes(
        hashes,
        aspects=["lxmf.delivery", "nomadnetwork.node"],
        blocked_identity_hashes=["blocked"],
    )
    assert len(out) == 2
    assert mock_db.provider.fetchall.call_count == 2
    first_sql, first_params = mock_db.provider.fetchall.call_args_list[0][0]
    assert "a.destination_hash IN (?, ?)" in first_sql
    assert "aa" in first_params
    assert "bb" in first_params
    assert "blocked" in first_params
