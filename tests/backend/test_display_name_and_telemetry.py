import base64
from unittest.mock import MagicMock, patch

import LXMF
import RNS.vendor.umsgpack as msgpack

from meshchatx.src.backend.meshchat_utils import parse_lxmf_display_name
from meshchatx.src.backend.telemetry_utils import Telemeter


def test_parse_lxmf_display_name_bytes_and_strings_in_msgpack_list():
    """``parse_lxmf_display_name`` accepts msgpack list elements as bytes or str."""
    display_name_bytes = b"Test User"
    app_data_list = [display_name_bytes, None, None]
    app_data_bytes = msgpack.packb(app_data_list)
    app_data_base64 = base64.b64encode(app_data_bytes).decode()

    assert parse_lxmf_display_name(app_data_base64) == "Test User"

    display_name_str = "Test User Str"
    app_data_list_str = [display_name_str, None, None]

    with patch("RNS.vendor.umsgpack.unpackb", return_value=app_data_list_str):
        assert parse_lxmf_display_name(app_data_base64) == "Test User Str"

    assert parse_lxmf_display_name(app_data_bytes) == "Test User"


def test_lxmf_telemetry_decoding():
    """Test decoding of LXMF telemetry fields."""
    # Create some dummy telemetry data
    ts = 1736264575
    lat, lon = 52.5200, 13.4050

    # Use Telemeter.pack to create valid telemetry bytes
    location = {
        "latitude": lat,
        "longitude": lon,
        "altitude": 100,
        "speed": 10,
        "bearing": 90,
        "accuracy": 5,
        "last_update": ts,
    }

    packed_telemetry = Telemeter.pack(time_utc=ts, location=location)

    # Decode it back
    unpacked = Telemeter.from_packed(packed_telemetry)

    assert unpacked is not None
    assert unpacked["time"]["utc"] == ts
    assert unpacked["location"]["latitude"] == lat
    assert unpacked["location"]["longitude"] == lon
    assert unpacked["location"]["altitude"] == 100.0
    assert unpacked["location"]["speed"] == 10.0
    assert unpacked["location"]["bearing"] == 90.0
    assert unpacked["location"]["accuracy"] == 5.0


def test_lxmf_telemetry_mapping_in_app():
    """Test how the app handles telemetry fields from an LXMF message."""
    # Mock lxmf_message
    lxmf_message = MagicMock(spec=LXMF.LXMessage)
    source_hash = b"\x01" * 32
    lxmf_message.source_hash = source_hash
    lxmf_message.hash = b"\x02" * 32

    ts = 1736264575
    packed_telemetry = Telemeter.pack(
        time_utc=ts,
        location={"latitude": 1.23, "longitude": 4.56},
    )

    lxmf_message.get_fields.return_value = {LXMF.FIELD_TELEMETRY: packed_telemetry}

    # Test unpacking directly using the same logic as in meshchat.py
    fields = lxmf_message.get_fields()
    assert LXMF.FIELD_TELEMETRY in fields

    telemetry_data = fields[LXMF.FIELD_TELEMETRY]
    unpacked = Telemeter.from_packed(telemetry_data)

    assert unpacked["time"]["utc"] == ts
    assert unpacked["location"]["latitude"] == 1.23
    assert unpacked["location"]["longitude"] == 4.56
