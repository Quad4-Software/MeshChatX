# SPDX-License-Identifier: 0BSD

import time

from meshchatx.src.backend.telemetry_utils import Telemeter


def test_pack_unpack_location():
    lat, lon = 52.5200, 13.4050
    alt, speed, bearing, acc = 100.5, 5.25, 180, 2.5
    ts = int(time.time())

    packed = Telemeter.pack_location(lat, lon, alt, speed, bearing, acc, ts)

    assert packed is not None
    assert len(packed) == 7

    unpacked = Telemeter.unpack_location(packed)

    assert unpacked["latitude"] == lat
    assert unpacked["longitude"] == lon
    assert unpacked["altitude"] == alt
    assert unpacked["speed"] == speed
    assert unpacked["bearing"] == bearing
    assert unpacked["accuracy"] == acc
    assert unpacked["last_update"] == ts


def test_pack_unpack_full_telemetry():
    location = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "altitude": 10.0,
        "speed": 0.0,
        "bearing": 0,
        "accuracy": 5.0,
    }
    ts = int(time.time())

    packed_blob = Telemeter.pack(time_utc=ts, location=location)
    assert isinstance(packed_blob, bytes)

    unpacked = Telemeter.from_packed(packed_blob)
    assert unpacked["time"]["utc"] == ts
    assert unpacked["location"]["latitude"] == location["latitude"]
    assert unpacked["location"]["longitude"] == location["longitude"]
