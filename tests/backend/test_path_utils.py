# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock

import pytest
import RNS

from meshchatx.src.backend.path_utils import (
    MIN_WINDOW_BITRATE,
    PATH_EXCHANGE_BYTES,
    path_response_window,
    slowest_online_bitrate,
)

DEST = bytes(16)


def _bitrate_floor_s(bitrate: float) -> float:
    return 2 * (PATH_EXCHANGE_BYTES * 8 / max(bitrate, MIN_WINDOW_BITRATE)) + 10


def test_slowest_online_bitrate_picks_min_up_interface():
    reticulum = MagicMock()
    reticulum.get_interface_stats.return_value = {
        "interfaces": [
            {"status": False, "bitrate": 50},
            {"status": True, "bitrate": 1200},
            {"status": True, "bitrate": 300},
            {"status": True},
        ],
    }
    assert slowest_online_bitrate(reticulum) == 300


def test_slowest_online_bitrate_none_when_stats_missing_or_fail():
    reticulum = MagicMock()
    reticulum.get_interface_stats.return_value = {"interfaces": []}
    assert slowest_online_bitrate(reticulum) is None

    reticulum.get_interface_stats.return_value = {}
    assert slowest_online_bitrate(reticulum) is None

    reticulum.get_interface_stats.side_effect = RuntimeError("stats unavailable")
    assert slowest_online_bitrate(reticulum) is None


def test_path_response_window_uses_slow_bitrate_airtime_floor():
    reticulum = MagicMock()
    reticulum.get_first_hop_timeout.return_value = 2.0
    reticulum.get_interface_stats.return_value = {
        "interfaces": [
            {"status": True, "bitrate": 100},
            {"status": True, "bitrate": 10_000},
            {"status": False, "bitrate": 10},
        ],
    }
    window = path_response_window(DEST, reticulum)
    expected = max(2.0, _bitrate_floor_s(100), RNS.Transport.PATH_REQUEST_TIMEOUT)
    assert window == pytest.approx(expected)
    assert expected == pytest.approx(48.4)


def test_path_response_window_never_below_rns_path_request_timeout():
    reticulum = MagicMock()
    reticulum.get_first_hop_timeout.return_value = 0.1
    reticulum.get_interface_stats.return_value = {
        "interfaces": [{"status": True, "bitrate": 1_000_000}],
    }
    window = path_response_window(DEST, reticulum)
    assert window >= RNS.Transport.PATH_REQUEST_TIMEOUT
    assert window == float(RNS.Transport.PATH_REQUEST_TIMEOUT)
