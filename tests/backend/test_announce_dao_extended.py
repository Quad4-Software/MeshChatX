import os
import tempfile

import pytest

from meshchatx.src.backend.database.announces import AnnounceDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def announce_dao(temp_db):
    provider = DatabaseProvider(temp_db)
    schema = DatabaseSchema(provider)
    schema.initialize()
    dao = AnnounceDAO(provider)
    yield dao
    provider.close()


def test_get_filtered_announces_identity_hash(announce_dao):
    # Setup: Insert some dummy announces
    announce_dao.upsert_announce(
        {
            "destination_hash": "dest1",
            "aspect": "lxmf.propagation",
            "identity_hash": "ident1",
            "identity_public_key": "pub1",
            "app_data": "data1",
            "rssi": -50,
            "snr": 10,
            "quality": 1.0,
        },
    )
    announce_dao.upsert_announce(
        {
            "destination_hash": "dest2",
            "aspect": "lxmf.delivery",
            "identity_hash": "ident1",
            "identity_public_key": "pub1",
            "app_data": "data2",
            "rssi": -50,
            "snr": 10,
            "quality": 1.0,
        },
    )
    announce_dao.upsert_announce(
        {
            "destination_hash": "dest3",
            "aspect": "lxmf.delivery",
            "identity_hash": "ident2",
            "identity_public_key": "pub2",
            "app_data": "data3",
            "rssi": -50,
            "snr": 10,
            "quality": 1.0,
        },
    )

    # Test filtering by identity_hash
    results = announce_dao.get_filtered_announces(identity_hash="ident1")
    assert len(results) == 2
    assert all(r["identity_hash"] == "ident1" for r in results)

    # Test filtering by identity_hash and aspect
    results = announce_dao.get_filtered_announces(
        identity_hash="ident1",
        aspect="lxmf.propagation",
    )
    assert len(results) == 1
    assert results[0]["destination_hash"] == "dest1"

    # Test filtering by destination_hash
    results = announce_dao.get_filtered_announces(destination_hash="dest2")
    assert len(results) == 1
    assert results[0]["identity_hash"] == "ident1"


def test_get_filtered_announces_robustness(announce_dao):
    # Test with non-existent identity_hash
    results = announce_dao.get_filtered_announces(identity_hash="non_existent")
    assert len(results) == 0

    # Test with multiple filters that yield no results
    results = announce_dao.get_filtered_announces(
        identity_hash="ident1",
        aspect="non_existent_aspect",
    )
    assert len(results) == 0


def test_get_announce_count_by_aspect(announce_dao):
    announce_dao.upsert_announce(
        {
            "destination_hash": "d1",
            "aspect": "lxmf.delivery",
            "identity_hash": "i1",
            "identity_public_key": "p1",
            "app_data": None,
            "rssi": -50,
            "snr": 10,
            "quality": 1.0,
        },
    )
    announce_dao.upsert_announce(
        {
            "destination_hash": "d2",
            "aspect": "lxmf.delivery",
            "identity_hash": "i2",
            "identity_public_key": "p2",
            "app_data": None,
            "rssi": -50,
            "snr": 10,
            "quality": 1.0,
        },
    )
    announce_dao.upsert_announce(
        {
            "destination_hash": "d3",
            "aspect": "nomadnetwork.node",
            "identity_hash": "i3",
            "identity_public_key": "p3",
            "app_data": None,
            "rssi": -50,
            "snr": 10,
            "quality": 1.0,
        },
    )

    assert announce_dao.get_announce_count_by_aspect("lxmf.delivery") == 2
    assert announce_dao.get_announce_count_by_aspect("nomadnetwork.node") == 1
    assert announce_dao.get_announce_count_by_aspect("lxmf.propagation") == 0
