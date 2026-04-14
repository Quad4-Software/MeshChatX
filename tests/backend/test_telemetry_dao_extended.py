import json
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.database.telemetry import TelemetryDAO


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
