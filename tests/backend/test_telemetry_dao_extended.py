# SPDX-License-Identifier: 0BSD

import json
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.database.telemetry import (
    MAX_TELEMETRY_ROWS_PER_DESTINATION,
    TelemetryDAO,
)


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def telemetry_dao(mock_provider):
    return TelemetryDAO(mock_provider)


def test_upsert_telemetry(telemetry_dao, mock_provider):
    telemetry_dao.upsert_telemetry("dest1", 12345, "data", physical_link={"rssi": -50})
    args, _ = mock_provider.execute.call_args
    assert "INSERT INTO lxmf_telemetry" in args[0]
    assert args[1][0] == "dest1"
    assert args[1][1] == 12345
    assert json.loads(args[1][4]) == {"rssi": -50}


def test_get_latest_telemetry(telemetry_dao, mock_provider):
    telemetry_dao.get_latest_telemetry("dest1")
    mock_provider.fetchone.assert_called_with(
        "SELECT * FROM lxmf_telemetry WHERE destination_hash = ? ORDER BY timestamp DESC LIMIT 1",
        ("dest1",),
    )


def test_is_tracking(telemetry_dao, mock_provider):
    mock_provider.fetchone.return_value = {"is_tracking": 1}
    assert telemetry_dao.is_tracking("dest1") is True

    mock_provider.fetchone.return_value = None
    assert telemetry_dao.is_tracking("dest2") is False


def test_toggle_tracking(telemetry_dao, mock_provider):
    # Mock is_tracking to return False
    mock_provider.fetchone.return_value = {"is_tracking": 0}
    res = telemetry_dao.toggle_tracking("dest1")
    assert res is True

    args, _ = mock_provider.execute.call_args
    assert args[1][1] == 1  # is_tracking = True


def test_update_last_request_at(telemetry_dao, mock_provider):
    telemetry_dao.update_last_request_at("dest1", 1000)
    args, _ = mock_provider.execute.call_args
    assert "UPDATE telemetry_tracking" in args[0]
    assert args[1] == (1000, "dest1")


def test_trim_telemetry_for_destination_caps_oldest(db):
    dao = db.telemetry
    for i in range(10):
        dao.upsert_telemetry("destA", 1000.0 + i, b"d")
        dao.upsert_telemetry("destB", 2000.0 + i, b"d")

    dao.trim_telemetry_for_destination("destA", max_rows=3)

    rows = dao.get_telemetry_history("destA", limit=50)
    assert [r["timestamp"] for r in rows] == [1009.0, 1008.0, 1007.0]
    # Other destinations are untouched.
    assert len(dao.get_telemetry_history("destB", limit=50)) == 10


def test_trim_telemetry_for_destination_noop_at_or_under_cap(db):
    dao = db.telemetry
    for i in range(3):
        dao.upsert_telemetry("destA", 1000.0 + i, b"d")
    dao.trim_telemetry_for_destination("destA", max_rows=3)
    dao.trim_telemetry_for_destination("destA", max_rows=10)
    assert len(dao.get_telemetry_history("destA", limit=50)) == 3


def test_upsert_telemetry_enforces_default_cap(db):
    dao = db.telemetry
    total = MAX_TELEMETRY_ROWS_PER_DESTINATION + 5
    for i in range(total):
        dao.upsert_telemetry("destA", 1000.0 + i, b"d")
    rows = dao.get_telemetry_history(
        "destA",
        limit=MAX_TELEMETRY_ROWS_PER_DESTINATION + 10,
    )
    assert len(rows) == MAX_TELEMETRY_ROWS_PER_DESTINATION
    assert min(r["timestamp"] for r in rows) == 1000.0 + 5
