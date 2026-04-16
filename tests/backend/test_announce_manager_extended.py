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
