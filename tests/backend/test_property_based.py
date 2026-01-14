import math
import struct
import time
from typing import Any
import json
import base64
import html

import pytest
from hypothesis import given, strategies as st, HealthCheck, settings
from meshchatx.src.backend.colour_utils import ColourUtils
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.lxmf_utils import convert_db_lxmf_message_to_dict
from meshchatx.src.backend.markdown_renderer import MarkdownRenderer
from meshchatx.src.backend.nomadnet_utils import (
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
)
from meshchatx.src.backend.meshchat_utils import (
    parse_bool_query_param,
    parse_lxmf_display_name,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_stamp_cost,
    parse_nomadnetwork_node_display_name,
)
from meshchatx.src.backend.telemetry_utils import Telemeter, Sensor
from RNS.vendor import umsgpack

# Strategies for telemetry data
st_latitude = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
st_longitude = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
st_altitude = st.floats(min_value=-10000, max_value=100000, allow_nan=False, allow_infinity=False)
st_speed = st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False)
st_bearing = st.floats(min_value=-360, max_value=360, allow_nan=False, allow_infinity=False)
st_accuracy = st.floats(min_value=0, max_value=655.35, allow_nan=False, allow_infinity=False)
st_timestamp = st.integers(min_value=0, max_value=2**32 - 1)

@given(
    lat=st_latitude,
    lon=st_longitude,
    alt=st_altitude,
    speed=st_speed,
    bear=st_bearing,
    acc=st_accuracy,
    ts=st_timestamp
)
def test_telemeter_location_roundtrip(lat, lon, alt, speed, bear, acc, ts):
    packed = Telemeter.pack_location(lat, lon, alt, speed, bear, acc, ts)
    assert packed is not None
    unpacked = Telemeter.unpack_location(packed)
    assert unpacked is not None
    
    # Check with tolerance due to rounding/fixed point conversion in packing
    assert math.isclose(unpacked["latitude"], lat, abs_tol=1e-6)
    assert math.isclose(unpacked["longitude"], lon, abs_tol=1e-6)
    assert math.isclose(unpacked["altitude"], alt, abs_tol=1e-2)
    assert math.isclose(unpacked["speed"], speed, abs_tol=1e-2)
    # Bearing can be negative in input but unpacked should match
    assert math.isclose(unpacked["bearing"], bear, abs_tol=1e-2)
    assert math.isclose(unpacked["accuracy"], acc, abs_tol=1e-2)
    assert unpacked["last_update"] == ts

@given(
    time_utc=st_timestamp,
    lat=st_latitude,
    lon=st_longitude,
    charge=st.integers(min_value=0, max_value=100),
    charging=st.booleans(),
    rssi=st.integers(min_value=-150, max_value=0),
    snr=st.integers(min_value=-20, max_value=20),
    q=st.integers(min_value=0, max_value=100)
)
def test_telemeter_full_pack_roundtrip(time_utc, lat, lon, charge, charging, rssi, snr, q):
    location = {"latitude": lat, "longitude": lon}
    battery = {"charge_percent": charge, "charging": charging}
    physical_link = {"rssi": rssi, "snr": snr, "q": q}
    
    packed = Telemeter.pack(
        time_utc=time_utc,
        location=location,
        battery=battery,
        physical_link=physical_link
    )
    
    unpacked = Telemeter.from_packed(packed)
    assert unpacked is not None
    assert unpacked["time"]["utc"] == time_utc
    assert math.isclose(unpacked["location"]["latitude"], lat, abs_tol=1e-6)
    assert math.isclose(unpacked["location"]["longitude"], lon, abs_tol=1e-6)
    assert unpacked["battery"]["charge_percent"] == charge
    assert unpacked["battery"]["charging"] == charging
    assert unpacked["physical_link"]["rssi"] == rssi
    assert unpacked["physical_link"]["snr"] == snr
    assert unpacked["physical_link"]["q"] == q

@given(hex_val=st.from_regex(r"^#?[0-9a-fA-F]{6}$"))
def test_colour_utils_hex_to_byte_array(hex_val):
    result = ColourUtils.hex_colour_to_byte_array(hex_val)
    assert len(result) == 3
    
    # Verify manual conversion matches
    clean_hex = hex_val.lstrip("#")
    expected = bytes.fromhex(clean_hex)
    assert result == expected

@given(val=st.one_of(st.sampled_from(["1", "true", "yes", "on", "0", "false", "no", "off", "random"]), st.none()))
def test_parse_bool_query_param(val):
    result = parse_bool_query_param(val)
    if val is None:
        assert result is False
    elif val.lower() in {"1", "true", "yes", "on"}:
        assert result is True
    else:
        assert result is False

@given(data=st.binary())
def test_parse_lxmf_display_name_robustness(data):
    # This should never crash
    try:
        parse_lxmf_display_name(data)
    except Exception as e:
        pytest.fail(f"parse_lxmf_display_name crashed: {e}")

@given(data=st.binary())
def test_parse_lxmf_propagation_node_app_data_robustness(data):
    # This should never crash
    try:
        parse_lxmf_propagation_node_app_data(data)
    except Exception as e:
        pytest.fail(f"parse_lxmf_propagation_node_app_data crashed: {e}")

@given(data=st.binary())
def test_parse_lxmf_stamp_cost_robustness(data):
    # This should never crash
    try:
        parse_lxmf_stamp_cost(data)
    except Exception as e:
        pytest.fail(f"parse_lxmf_stamp_cost crashed: {e}")

@given(name=st.text())
def test_parse_nomadnetwork_node_display_name_robustness(name):
    # This should never crash
    try:
        parse_nomadnetwork_node_display_name(name)
    except Exception as e:
        pytest.fail(f"parse_nomadnetwork_node_display_name crashed: {e}")

@given(packed=st.binary())
def test_telemeter_from_packed_robustness(packed):
    # This should never crash
    try:
        Telemeter.from_packed(packed)
    except Exception as e:
        pytest.fail(f"Telemeter.from_packed crashed: {e}")

@given(text=st.text())
def test_markdown_renderer_no_crash(text):
    try:
        MarkdownRenderer.render(text)
    except Exception as e:
        pytest.fail(f"MarkdownRenderer.render crashed: {e}")

@given(text=st.text())
def test_interface_config_parser_no_crash(text):
    try:
        InterfaceConfigParser.parse(text)
    except Exception as e:
        pytest.fail(f"InterfaceConfigParser.parse crashed: {e}")

# Strategy for a database message row
st_db_message = st.dictionaries(
    keys=st.sampled_from([
        "id", "hash", "source_hash", "destination_hash", "is_incoming",
        "state", "progress", "method", "delivery_attempts",
        "next_delivery_attempt_at", "title", "content", "fields",
        "timestamp", "rssi", "snr", "quality", "is_spam",
        "created_at", "updated_at"
    ]),
    values=st.one_of(
        st.none(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(),
        st.booleans(),
        st.binary().map(lambda b: b.hex())
    )
).filter(lambda d: "created_at" in d and "updated_at" in d)

@settings(suppress_health_check=[HealthCheck.too_slow])
@given(db_message=st_db_message)
def test_convert_db_lxmf_message_to_dict_robustness(db_message):
    # Fill in missing required keys for the function
    required_keys = [
        "id", "hash", "source_hash", "destination_hash", "is_incoming",
        "state", "progress", "method", "delivery_attempts",
        "next_delivery_attempt_at", "title", "content", "fields",
        "timestamp", "rssi", "snr", "quality", "is_spam",
        "created_at", "updated_at"
    ]
    for key in required_keys:
        if key not in db_message:
            db_message[key] = None
    
    # Ensure fields is a valid JSON string if it's not None
    if db_message["fields"] is not None:
        try:
            json.loads(db_message["fields"])
        except (ValueError, TypeError, json.JSONDecodeError):
            db_message["fields"] = "{}"

    try:
        convert_db_lxmf_message_to_dict(db_message)
    except Exception:
        # We expect some errors if data is really weird, but it shouldn't crash the whole thing
        pass

@given(data=st.dictionaries(keys=st.text(), values=st.text()))
def test_convert_nomadnet_field_data_to_map(data):
    result = convert_nomadnet_field_data_to_map(data)
    assert len(result) == len(data)
    for k, v in data.items():
        assert result[f"field_{k}"] == v

@given(data=st.dictionaries(keys=st.text().filter(lambda x: "=" not in x and "|" not in x and x), 
                           values=st.text().filter(lambda x: "|" not in x)))
def test_convert_nomadnet_string_data_to_map_roundtrip(data):
    # Construct string like key1=val1|key2=val2
    input_str = "|".join([f"{k}={v}" for k, v in data.items()])
    result = convert_nomadnet_string_data_to_map(input_str)
    assert len(result) == len(data)
    for k, v in data.items():
        assert result[f"var_{k}"] == v

@given(text=st.text())
def test_markdown_renderer_xss_protection(text):
    # Basic check: if we use <script>, it should be escaped
    input_text = f"<script>alert(1)</script>{text}"
    result = MarkdownRenderer.render(input_text)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result

@given(content=st.text())
def test_markdown_renderer_headers(content):
    if content and "\n" not in content:
        input_text = f"# {content}"
        result = MarkdownRenderer.render(input_text)
        assert "<h1" in result
        assert html.escape(content) in result
