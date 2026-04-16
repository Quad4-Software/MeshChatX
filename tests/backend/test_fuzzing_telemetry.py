# SPDX-License-Identifier: 0BSD

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.telemetry_utils import Telemeter

# Strategies for telemetry data
st_lat_lon = st.floats(min_value=-90, max_value=90)
st_alt = st.floats(min_value=-10000, max_value=100000)
st_speed = st.floats(min_value=0, max_value=2000)
st_bearing = st.floats(min_value=0, max_value=360)
st_accuracy = st.floats(min_value=0, max_value=10000)
st_timestamp = st.integers(min_value=0, max_value=2**32 - 1)


@settings(deadline=None)
@given(
    lat=st_lat_lon,
    lon=st_lat_lon,
    alt=st_alt,
    speed=st_speed,
    bearing=st_bearing,
    acc=st_accuracy,
    ts=st_timestamp,
)
def test_fuzz_pack_location(lat, lon, alt, speed, bearing, acc, ts):
    packed = Telemeter.pack_location(lat, lon, alt, speed, bearing, acc, ts)
    if packed is not None:
        unpacked = Telemeter.unpack_location(packed)
        if unpacked:
            # Check for reasonable precision (we use 1e6 for lat/lon, 1e2 for others)
            assert abs(unpacked["latitude"] - lat) < 0.000002
            assert abs(unpacked["longitude"] - lon) < 0.000002
            assert abs(unpacked["altitude"] - alt) < 0.02
            assert abs(unpacked["speed"] - speed) < 0.02
            assert abs(unpacked["bearing"] - bearing) < 0.02
            assert abs(unpacked["accuracy"] - acc) < 0.02
            assert unpacked["last_update"] == ts


@settings(deadline=None)
@given(
    charge=st.integers(min_value=0, max_value=100),
    charging=st.integers(min_value=0, max_value=1),
    rssi=st.integers(min_value=-150, max_value=0),
    snr=st.floats(min_value=-20, max_value=20),
    q=st.integers(min_value=0, max_value=100),
)
def test_fuzz_full_telemetry_packing(charge, charging, rssi, snr, q):
    battery = {"charge_percent": charge, "charging": charging}
    physical_link = {"rssi": rssi, "snr": snr, "q": q}

    packed = Telemeter.pack(battery=battery, physical_link=physical_link)
    unpacked = Telemeter.from_packed(packed)

    assert unpacked["battery"]["charge_percent"] == charge
    assert unpacked["battery"]["charging"] == charging
    assert unpacked["physical_link"]["rssi"] == rssi
    assert abs(unpacked["physical_link"]["snr"] - snr) < 0.01
    assert unpacked["physical_link"]["q"] == q


@settings(deadline=None)
@given(data=st.binary(min_size=0, max_size=2000))
def test_fuzz_from_packed_random_bytes(data):
    try:
        Telemeter.from_packed(data)
    except Exception:
        pass


@settings(deadline=None)
@given(
    commands=st.lists(
        st.dictionaries(
            keys=st.one_of(st.integers(), st.text()),
            values=st.one_of(st.integers(), st.text(), st.floats(), st.booleans()),
        ),
        max_size=10,
    ),
)
def test_fuzz_command_parsing(commands):
    # This simulates how commands are handled in meshchat.py
    processed_commands = []
    for cmd in commands:
        new_cmd = {}
        for k, v in cmd.items():
            try:
                if isinstance(k, str):
                    if k.startswith("0x"):
                        new_cmd[int(k, 16)] = v
                    else:
                        new_cmd[int(k)] = v
                else:
                    new_cmd[k] = v
            except (ValueError, TypeError):
                new_cmd[k] = v
        processed_commands.append(new_cmd)

    assert len(processed_commands) == len(commands)
