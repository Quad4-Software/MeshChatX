# SPDX-License-Identifier: 0BSD

import math
import time

from RNS.vendor import umsgpack

from meshchatx.src.backend.telemetry_utils import Sensor, Telemeter


def test_pack_unpack_battery_and_link():
    battery = {"charge_percent": 85, "charging": 1}
    physical_link = {"rssi": -90, "snr": 8, "q": 95}
    ts = int(time.time())

    packed = Telemeter.pack(time_utc=ts, battery=battery, physical_link=physical_link)
    assert isinstance(packed, bytes)

    unpacked = Telemeter.from_packed(packed)
    assert unpacked["time"]["utc"] == ts
    assert unpacked["battery"]["charge_percent"] == battery["charge_percent"]
    assert unpacked["battery"]["charging"] is True
    assert unpacked["physical_link"]["rssi"] == physical_link["rssi"]
    assert unpacked["physical_link"]["snr"] == physical_link["snr"]
    assert unpacked["physical_link"]["q"] == physical_link["q"]


def test_telemeter_from_packed_robustness():
    # Test with corrupted umsgpack data
    assert Telemeter.from_packed(b"\xff\xff\xff") is None
    # Test with empty data
    assert Telemeter.from_packed(b"") is None
    # Test with valid umsgpack but unexpected structure
    invalid_structure = umsgpack.packb({"not_a_sensor": 123})
    assert Telemeter.from_packed(invalid_structure) == {}


def test_telemeter_unpack_location_robustness():
    # Test with insufficient elements
    assert Telemeter.unpack_location([b"lat", b"lon"]) is None
    # Test with invalid types
    assert Telemeter.unpack_location(["not_bytes"] * 7) is None


def test_telemeter_rejects_non_finite_sensor_values():
    packed = umsgpack.packb(
        {
            Sensor.SID_TIME: math.nan,
            Sensor.SID_BATTERY: [math.inf, True],
            Sensor.SID_PHYSICAL_LINK: [True, math.nan, "q"],
        },
    )
    unpacked = Telemeter.from_packed(packed)
    assert "time" not in unpacked
    assert "battery" not in unpacked
    assert unpacked["physical_link"] == {"rssi": None, "snr": None, "q": None}


def test_telemeter_location_last_update_rejects_non_finite():
    loc = Telemeter.pack_location(1.0, 2.0, last_update=10)
    loc[6] = math.nan
    unpacked = Telemeter.unpack_location(loc)
    assert unpacked is not None
    assert unpacked["last_update"] is None
