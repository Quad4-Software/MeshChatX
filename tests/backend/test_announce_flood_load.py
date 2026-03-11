import os
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.announce_manager import AnnounceManager


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.provider = MagicMock()
    db.announces = MagicMock()
    return db


def test_flood_announces_no_limit(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    reticulum.get_packet_q.return_value = 3
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    for i in range(500):
        manager.upsert_announce(
            reticulum,
            identity,
            os.urandom(16),
            "lxmf.delivery",
            b"app_data",
            os.urandom(16),
        )

    assert mock_db.announces.upsert_announce.call_count == 500


def test_flood_announces_with_limit_caps_at_limit(mock_db):
    config = MagicMock()
    config.announce_limit_lxmf_delivery = MagicMock()
    config.announce_limit_lxmf_delivery.get.return_value = 50
    mock_db.announces.get_announce_by_hash.return_value = None

    count = [0]

    def get_count(aspect):
        return count[0]

    def on_upsert(*args, **kwargs):
        count[0] += 1

    mock_db.announces.get_announce_count_by_aspect.side_effect = get_count
    mock_db.announces.upsert_announce.side_effect = on_upsert

    manager = AnnounceManager(mock_db, config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    for i in range(100):
        manager.upsert_announce(
            reticulum,
            identity,
            os.urandom(16),
            "lxmf.delivery",
            b"app_data",
            os.urandom(16),
        )

    assert count[0] == 50


def test_load_rapid_nomadnet_announces(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    for i in range(200):
        manager.upsert_announce(
            reticulum,
            identity,
            os.urandom(16),
            "nomadnetwork.node",
            f"node_{i}".encode(),
            os.urandom(16),
        )

    assert mock_db.announces.upsert_announce.call_count == 200


def test_load_rapid_propagation_announces(mock_db):
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    for i in range(100):
        manager.upsert_announce(
            reticulum,
            identity,
            os.urandom(16),
            "lxmf.propagation",
            b"prop_data",
            os.urandom(16),
        )

    assert mock_db.announces.upsert_announce.call_count == 100
