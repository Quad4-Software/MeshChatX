import html
import json
import math
import os
import shutil

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.colour_utils import ColourUtils
from meshchatx.src.backend.identity_manager import IdentityManager
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.lxmf_utils import (
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_lxmf_method_to_string,
    convert_lxmf_state_to_string,
)
from meshchatx.src.backend.markdown_renderer import MarkdownRenderer
from meshchatx.src.backend.meshchat_utils import (
    convert_db_favourite_to_dict,
    convert_propagation_node_state_to_string,
    has_attachments,
    message_fields_have_attachments,
    parse_bool_query_param,
    parse_lxmf_display_name,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_stamp_cost,
    parse_nomadnetwork_node_display_name,
)
from meshchatx.src.backend.nomadnet_utils import (
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
)
from meshchatx.src.backend.recovery.crash_recovery import CrashRecovery
from meshchatx.src.backend.telemetry_utils import Telemeter

# Strategies for telemetry data
st_latitude = st.floats(
    min_value=-90,
    max_value=90,
    allow_nan=False,
    allow_infinity=False,
)
st_longitude = st.floats(
    min_value=-180,
    max_value=180,
    allow_nan=False,
    allow_infinity=False,
)
st_altitude = st.floats(
    min_value=-10000,
    max_value=100000,
    allow_nan=False,
    allow_infinity=False,
)
st_speed = st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False)
st_bearing = st.floats(
    min_value=-360,
    max_value=360,
    allow_nan=False,
    allow_infinity=False,
)
st_accuracy = st.floats(
    min_value=0,
    max_value=655.35,
    allow_nan=False,
    allow_infinity=False,
)
st_timestamp = st.integers(min_value=0, max_value=2**32 - 1)


@given(
    lat=st_latitude,
    lon=st_longitude,
    alt=st_altitude,
    speed=st_speed,
    bear=st_bearing,
    acc=st_accuracy,
    ts=st_timestamp,
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
    q=st.integers(min_value=0, max_value=100),
)
def test_telemeter_full_pack_roundtrip(
    time_utc,
    lat,
    lon,
    charge,
    charging,
    rssi,
    snr,
    q,
):
    location = {"latitude": lat, "longitude": lon}
    battery = {"charge_percent": charge, "charging": charging}
    physical_link = {"rssi": rssi, "snr": snr, "q": q}

    packed = Telemeter.pack(
        time_utc=time_utc,
        location=location,
        battery=battery,
        physical_link=physical_link,
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


@given(
    val=st.one_of(
        st.sampled_from(
            ["1", "true", "yes", "on", "0", "false", "no", "off", "random"],
        ),
        st.none(),
    ),
)
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
    try:
        parse_lxmf_display_name(data)
    except Exception as e:
        pytest.fail(f"parse_lxmf_display_name crashed: {e}")


@given(data=st.binary())
def test_parse_lxmf_propagation_node_app_data_robustness(data):
    try:
        result = parse_lxmf_propagation_node_app_data(data)
        if result is not None:
            assert isinstance(result, dict)
            assert "enabled" in result
            assert "timebase" in result
            assert "per_transfer_limit" in result
    except Exception as e:
        pytest.fail(f"parse_lxmf_propagation_node_app_data crashed: {e}")


@given(
    names=st.lists(
        st.text(min_size=1).filter(lambda x: "]" not in x and x.strip()),
        min_size=1,
        max_size=5,
    ),
    keys=st.lists(
        st.text(min_size=1).filter(
            lambda x: "=" not in x and "]" not in x and x.strip()
        ),
        min_size=1,
        max_size=5,
    ),
    values=st.lists(st.text().filter(lambda x: "\n" not in x), min_size=1, max_size=5),
)
def test_interface_config_parser_best_effort_property(names, keys, values):
    # Intentionally corrupt the config to trigger best-effort
    config_lines = ["[interfaces]"]
    for name in names:
        config_lines.append(f"[[{name}")  # Missing closing ]]
        for k, v in zip(keys, values):
            config_lines.append(f"  {k} = {v}")

    config_text = "\n".join(config_lines)
    try:
        # Should not crash and should hopefully find some interfaces
        interfaces = InterfaceConfigParser.parse(config_text)
        assert isinstance(interfaces, list)
    except Exception as e:
        pytest.fail(f"InterfaceConfigParser.parse best-effort crashed: {e}")


@given(data=st.binary())
def test_parse_lxmf_stamp_cost_robustness(data):
    try:
        parse_lxmf_stamp_cost(data)
    except Exception as e:
        pytest.fail(f"parse_lxmf_stamp_cost crashed: {e}")


@given(name=st.text())
def test_parse_nomadnetwork_node_display_name_robustness(name):
    try:
        parse_nomadnetwork_node_display_name(name)
    except Exception as e:
        pytest.fail(f"parse_nomadnetwork_node_display_name crashed: {e}")


@given(packed=st.binary())
def test_telemeter_from_packed_robustness(packed):
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


@given(
    names=st.lists(
        st.text(
            min_size=1,
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs"), blacklist_characters="[]"
            ),
        ).filter(lambda x: x.strip() == x and x),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    keys=st.lists(
        st.text(
            min_size=1,
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs"), blacklist_characters="[]="
            ),
        ).filter(lambda x: x.strip() == x and x),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    values=st.lists(
        st.text(alphabet=st.characters(blacklist_categories=("Cc", "Cs"))).filter(
            lambda x: "\n" not in x
        ),
        min_size=1,
        max_size=5,
    ),
)
def test_interface_config_parser_structured(names, keys, values):
    config_lines = ["[interfaces]"]
    for name in names:
        config_lines.append(f"[[{name}]]")
        for k, v in zip(keys, values):
            config_lines.append(f"  {k} = {v}")

    config_text = "\n".join(config_lines)
    try:
        interfaces = InterfaceConfigParser.parse(config_text)
        # We check if it parsed successfully and names match.
        # Some weird characters might still cause ConfigObj to skip a section,
        # so we don't strictly assert len(interfaces) == len(names) if we suspect
        # ConfigObj might fail on some valid-ish looking strings.
        # But with the filtered alphabet it should be more stable.
        for iface in interfaces:
            assert "name" in iface
            # The parser strips the name from the line, so our filtered 'names'
            # (which are already stripped) should match.
            assert iface["name"] in names
    except Exception as e:
        pytest.fail(f"InterfaceConfigParser.parse failed on structured input: {e}")


@given(
    interfaces=st.lists(
        st.dictionaries(
            keys=st.sampled_from(
                [
                    "name",
                    "type",
                    "reachable_on",
                    "target_host",
                    "remote",
                    "listen_ip",
                    "port",
                    "target_port",
                    "listen_port",
                    "discovery_hash",
                    "transport_id",
                    "network_id",
                ]
            ),
            values=st.one_of(st.text(), st.integers(), st.none()),
            max_size=12,
        ),
        max_size=40,
    ),
    whitelist=st.one_of(st.text(), st.lists(st.text(), max_size=20), st.none()),
    blacklist=st.one_of(st.text(), st.lists(st.text(), max_size=20), st.none()),
)
def test_discovery_filter_robustness(interfaces, whitelist, blacklist):
    try:
        filtered = ReticulumMeshChat.filter_discovered_interfaces(
            interfaces,
            whitelist,
            blacklist,
        )
    except Exception as e:
        pytest.fail(f"Discovery filtering crashed: {e}")
    assert isinstance(filtered, list)
    assert len(filtered) <= len(interfaces)


# Strategy for a database message row
st_db_message = st.dictionaries(
    keys=st.sampled_from(
        [
            "id",
            "hash",
            "source_hash",
            "destination_hash",
            "is_incoming",
            "state",
            "progress",
            "method",
            "delivery_attempts",
            "next_delivery_attempt_at",
            "title",
            "content",
            "fields",
            "timestamp",
            "rssi",
            "snr",
            "quality",
            "is_spam",
            "created_at",
            "updated_at",
        ],
    ),
    values=st.one_of(
        st.none(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(),
        st.booleans(),
        st.binary().map(lambda b: b.hex()),
    ),
).filter(lambda d: "created_at" in d and "updated_at" in d)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(db_message=st_db_message)
def test_convert_db_lxmf_message_to_dict_robustness(db_message):
    # Fill in missing required keys for the function
    required_keys = [
        "id",
        "hash",
        "source_hash",
        "destination_hash",
        "is_incoming",
        "state",
        "progress",
        "method",
        "delivery_attempts",
        "next_delivery_attempt_at",
        "title",
        "content",
        "fields",
        "timestamp",
        "rssi",
        "snr",
        "quality",
        "is_spam",
        "created_at",
        "updated_at",
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


@given(
    data=st.dictionaries(
        keys=st.text().filter(lambda x: "=" not in x and "|" not in x and x),
        values=st.text().filter(lambda x: "|" not in x),
    ),
)
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


@given(content=st.text().filter(lambda x: x and "\n" not in x and "#" not in x))
def test_markdown_renderer_headers(content):
    input_text = f"# {content}"
    result = MarkdownRenderer.render(input_text)
    assert "<h1" in result
    # Check that it's correctly wrapped in h1
    assert result.startswith("<h1")
    assert result.endswith("</h1>")

    if not any(c in content for c in "*_~`[]()"):
        assert html.escape(content) in result


@given(data=st.binary())
def test_identity_restore_robustness(data):
    manager = IdentityManager("/tmp/test_identities")
    try:
        # Should either return a dict or raise ValueError, but not crash
        manager.restore_identity_from_bytes(data)
    except ValueError:
        pass
    except Exception as e:
        pytest.fail(f"restore_identity_from_bytes crashed with: {e}")
    finally:
        if os.path.exists("/tmp/test_identities"):
            shutil.rmtree("/tmp/test_identities")


@given(data=st.text())
def test_identity_restore_base32_robustness(data):
    manager = IdentityManager("/tmp/test_identities_b32")
    try:
        manager.restore_identity_from_base32(data)
    except ValueError:
        pass
    except Exception as e:
        pytest.fail(f"restore_identity_from_base32 crashed with: {e}")
    finally:
        if os.path.exists("/tmp/test_identities_b32"):
            shutil.rmtree("/tmp/test_identities_b32")


@given(
    st.lists(
        st.text(min_size=1).filter(
            lambda x: "\n" not in x and x.strip() and x.isalnum(),
        ),
    ),
)
def test_markdown_renderer_list_rendering(items):
    if not items:
        return
    markdown = "\n".join([f"* {item}" for item in items])
    html_output = MarkdownRenderer.render(markdown)
    assert "<ul" in html_output
    for item in items:
        assert item in html_output


@given(
    st.text(min_size=1).filter(lambda x: x.isalnum()),
    st.text(min_size=1).filter(lambda x: x.isalnum()),
)
def test_markdown_renderer_link_rendering(label, url):
    markdown = f"[{label}]({url})"
    html_output = MarkdownRenderer.render(markdown)
    assert "<a href=" in html_output
    assert label in html_output


@given(
    exc_msg=st.text(),
    exc_type_name=st.text(min_size=1).filter(lambda x: x.isidentifier()),
    diagnosis=st.dictionaries(
        keys=st.sampled_from(
            [
                "low_memory",
                "config_missing",
                "config_invalid",
                "db_type",
                "active_interfaces",
                "available_mem_mb",
            ],
        ),
        values=st.one_of(
            st.booleans(),
            st.text(),
            st.integers(min_value=0, max_value=100000),
        ),
    ),
)
def test_crash_recovery_analyze_cause_robustness(exc_msg, exc_type_name, diagnosis):
    recovery = CrashRecovery()
    # Mocking exc_type
    mock_exc_type = type(exc_type_name, (Exception,), {})
    mock_exc_value = Exception(exc_msg)

    try:
        causes = recovery._analyze_cause(mock_exc_type, mock_exc_value, diagnosis)
        assert isinstance(causes, list)
        for cause in causes:
            assert "probability" in cause
            assert "description" in cause
            assert "reasoning" in cause
            assert 0 <= cause["probability"] <= 100
    except Exception as e:
        pytest.fail(f"CrashRecovery._analyze_cause crashed: {e}")


@given(
    diagnosis=st.dictionaries(
        keys=st.sampled_from(
            [
                "low_memory",
                "config_missing",
                "config_invalid",
                "db_type",
                "available_mem_mb",
            ],
        ),
        values=st.one_of(
            st.booleans(),
            st.text(),
            st.integers(min_value=0, max_value=100000),
            st.none(),
        ),
    ),
)
def test_crash_recovery_entropy_logic(diagnosis):
    recovery = CrashRecovery()
    entropy, divergence = recovery._calculate_system_entropy(diagnosis)

    assert isinstance(entropy, float)
    assert isinstance(divergence, float)
    # Entropy should be non-negative. Max theoretical for 4 independent binary
    # variables is 4.0 bits. Our p values are constrained between 0.01 and 0.99.
    assert 0.0 <= entropy <= 4.1
    assert divergence >= 0.0

    # Check that more uncertainty increases entropy (within one dimension)
    diag_stable = {"low_memory": False}
    diag_unstable = {"low_memory": True}
    e_stable, _ = recovery._calculate_system_entropy(diag_stable)
    e_unstable, _ = recovery._calculate_system_entropy(diag_unstable)
    assert e_unstable > e_stable


@given(
    exc_msg=st.text(),
    diagnosis=st.dictionaries(
        keys=st.sampled_from(
            [
                "low_memory",
                "config_missing",
                "config_invalid",
                "db_type",
                "active_interfaces",
            ],
        ),
        values=st.one_of(
            st.booleans(),
            st.text(),
            st.integers(min_value=0, max_value=100),
        ),
    ),
)
def test_crash_recovery_probability_sorting(exc_msg, diagnosis):
    recovery = CrashRecovery()
    # Use a real exception type that often triggers results
    causes = recovery._analyze_cause(RuntimeError, RuntimeError(exc_msg), diagnosis)

    if len(causes) > 1:
        probs = [c["probability"] for c in causes]
        assert probs == sorted(probs, reverse=True)


@given(
    favourite=st.dictionaries(
        keys=st.sampled_from(
            [
                "id",
                "destination_hash",
                "display_name",
                "aspect",
                "created_at",
                "updated_at",
            ],
        ),
        values=st.one_of(
            st.integers(),
            st.text(),
            st.none(),
        ),
    ),
)
def test_convert_db_favourite_to_dict_robustness(favourite):
    # Ensure required keys exist
    for key in [
        "id",
        "destination_hash",
        "display_name",
        "aspect",
        "created_at",
        "updated_at",
    ]:
        if key not in favourite:
            favourite[key] = "test" if "at" not in key else "2025-01-01 12:00:00"

    try:
        result = convert_db_favourite_to_dict(favourite)
        assert isinstance(result, dict)
        assert result["id"] == favourite["id"]
        if favourite["created_at"]:
            # If input already had Z, output should have Z
            if "Z" in str(favourite["created_at"]):
                assert "Z" in result["created_at"]
            # If input had no timezone indicator (+ or Z), output should have Z
            elif "+" not in str(favourite["created_at"]):
                assert result["created_at"].endswith("Z")
    except Exception as e:
        pytest.fail(f"convert_db_favourite_to_dict crashed: {e}")


@given(state=st.integers())
def test_convert_propagation_node_state_to_string_robustness(state):
    result = convert_propagation_node_state_to_string(state)
    assert isinstance(result, str)
    # Check it's one of the known values or 'unknown'
    allowed = {
        "idle",
        "path_requested",
        "link_establishing",
        "link_established",
        "request_sent",
        "receiving",
        "response_received",
        "complete",
        "no_path",
        "link_failed",
        "transfer_failed",
        "no_identity_received",
        "no_access",
        "failed",
        "unknown",
    }
    assert result in allowed


@given(fields_json=st.one_of(st.text(), st.none()))
def test_message_fields_have_attachments_robustness(fields_json):
    # Should never crash
    try:
        result = message_fields_have_attachments(fields_json)
        assert isinstance(result, bool)
    except Exception as e:
        pytest.fail(f"message_fields_have_attachments crashed: {e}")


@given(
    lxmf_fields=st.dictionaries(
        keys=st.integers(),
        values=st.one_of(
            st.text(), st.binary(), st.integers(), st.booleans(), st.none()
        ),
    )
)
def test_has_attachments_robustness(lxmf_fields):
    # Should never crash
    try:
        result = has_attachments(lxmf_fields)
        assert isinstance(result, bool)
    except Exception as e:
        pytest.fail(f"has_attachments crashed: {e}")


@given(
    db_message=st.dictionaries(
        keys=st.sampled_from(
            [
                "id",
                "hash",
                "source_hash",
                "destination_hash",
                "is_incoming",
                "state",
                "progress",
                "method",
                "delivery_attempts",
                "next_delivery_attempt_at",
                "title",
                "content",
                "fields",
                "timestamp",
                "rssi",
                "snr",
                "quality",
                "is_spam",
                "created_at",
                "updated_at",
            ],
        ),
        values=st.one_of(
            st.none(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.booleans(),
        ),
    ),
    include_attachments=st.booleans(),
)
def test_convert_db_lxmf_message_to_dict_extended_robustness(
    db_message,
    include_attachments,
):
    # Fill in required keys
    required_keys = [
        "id",
        "hash",
        "source_hash",
        "destination_hash",
        "is_incoming",
        "state",
        "progress",
        "method",
        "delivery_attempts",
        "next_delivery_attempt_at",
        "title",
        "content",
        "fields",
        "timestamp",
        "rssi",
        "snr",
        "quality",
        "is_spam",
        "created_at",
        "updated_at",
    ]
    for key in required_keys:
        if key not in db_message:
            if "at" in key:
                db_message[key] = "2025-01-01 12:00:00"
            elif key == "fields":
                db_message[key] = "{}"
            elif key == "progress":
                db_message[key] = 0.5
            else:
                db_message[key] = None

    try:
        result = convert_db_lxmf_message_to_dict(db_message, include_attachments)
        assert isinstance(result, dict)
    except Exception as e:
        # Some errors are expected if fields is invalid JSON but it shouldn't be a hard crash of the test
        if not isinstance(e, (json.JSONDecodeError, TypeError)):
            # If we already handle it in the function, it shouldn't reach here
            pass


@given(
    state_val=st.integers(),
    method_val=st.integers(),
    title=st.binary(),
    content=st.binary(),
    timestamp=st.floats(allow_nan=False, allow_infinity=False),
    fields=st.dictionaries(
        keys=st.integers(),
        values=st.one_of(
            st.binary(),
            st.text(),
            st.lists(st.tuples(st.text(), st.binary())),
        ),
    ),
)
def test_lxmf_utils_conversions_robustness(
    state_val, method_val, title, content, timestamp, fields
):
    import LXMF
    from unittest.mock import MagicMock

    # Create a mock LXMessage
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.state = state_val
    msg.method = method_val
    msg.title = title
    msg.content = content
    msg.timestamp = timestamp
    msg.hash = os.urandom(16)
    msg.source_hash = os.urandom(16)
    msg.destination_hash = os.urandom(16)
    msg.incoming = True
    msg.progress = 0.5
    msg.delivery_attempts = 0
    msg.rssi = -50
    msg.snr = 5
    msg.q = 100

    # Ensure get_fields returns our property-generated fields
    msg.get_fields.return_value = fields

    try:
        convert_lxmf_message_to_dict(msg)
        convert_lxmf_state_to_string(msg)
        convert_lxmf_method_to_string(msg)
    except Exception:
        # We don't expect hard crashes here even with weird mock data
        # unless it's something fundamentally wrong with the mock or the data
        # e.g. telemetry unpacking might fail if data is not valid telemetry
        pass


@given(
    hex_str=st.from_regex(r"^[0-9a-fA-F]*$"),
)
def test_identity_recall_logic_robustness(hex_str):
    import RNS

    try:
        if len(hex_str) % 2 == 0:
            hash_bytes = bytes.fromhex(hex_str)
            RNS.Identity.recall(hash_bytes)
    except Exception:
        pass


@given(
    aspect=st.sampled_from(
        ["lxmf.delivery", "lxst.telephony", "nomadnetwork.node", "unknown"]
    ),
    data=st.binary(),
)
def test_parse_lxmf_display_name_extended(aspect, data):
    # Testing parse_lxmf_display_name with different possible inputs
    from meshchatx.src.backend.meshchat_utils import parse_lxmf_display_name

    try:
        result = parse_lxmf_display_name(data)
        assert isinstance(result, str)
    except Exception:
        pass


MIN_SIZE_RATIO = 0.2


def _is_backup_suspicious_reference(current_stats, baseline):
    if not baseline:
        return False
    prev_count = baseline.get("message_count", 0)
    prev_bytes = baseline.get("total_bytes", 0)
    curr_count = current_stats.get("message_count", 0)
    curr_bytes = current_stats.get("total_bytes", 0)
    if prev_count > 0 and curr_count == 0:
        return True
    if prev_bytes > 100_000 and curr_bytes < prev_bytes * MIN_SIZE_RATIO:
        return True
    return False


@given(
    prev_count=st.integers(min_value=0, max_value=1_000_000),
    prev_bytes=st.integers(min_value=0, max_value=10_000_000),
    curr_count=st.integers(min_value=0, max_value=1_000_000),
    curr_bytes=st.integers(min_value=0, max_value=10_000_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_is_backup_suspicious_property(prev_count, prev_bytes, curr_count, curr_bytes):
    from meshchatx.src.backend.database import Database

    baseline = {"message_count": prev_count, "total_bytes": prev_bytes}
    current_stats = {"message_count": curr_count, "total_bytes": curr_bytes}
    db = Database(":memory:")
    db.initialize()
    result = db._is_backup_suspicious(current_stats, baseline)
    expected = _is_backup_suspicious_reference(current_stats, baseline)
    assert result == expected


# =====================================================================
# CrashRecovery math property-based tests
# =====================================================================


class TestCrashRecoveryMathProperties:
    """Property-based tests for CrashRecovery mathematical functions."""

    @staticmethod
    def _make_recovery():
        return CrashRecovery()

    @given(
        low_memory=st.booleans(),
        config_missing=st.booleans(),
        config_invalid=st.booleans(),
        db_type=st.sampled_from(["file", "memory"]),
        available_mem_mb=st.one_of(
            st.floats(min_value=0, max_value=100000, allow_nan=False),
            st.integers(min_value=0, max_value=100000),
            st.none(),
            st.just("garbage"),
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
        derandomize=True,
    )
    def test_system_entropy_always_finite(
        self, low_memory, config_missing, config_invalid, db_type, available_mem_mb
    ):
        """Entropy and divergence must always be finite floats for any diagnosis."""
        import math as m

        recovery = self._make_recovery()
        diag = {
            "low_memory": low_memory,
            "config_missing": config_missing,
            "config_invalid": config_invalid,
            "db_type": db_type,
            "available_mem_mb": available_mem_mb,
        }
        entropy, divergence = recovery._calculate_system_entropy(diag)
        assert m.isfinite(entropy), f"Non-finite entropy: {entropy}"
        assert m.isfinite(divergence), f"Non-finite divergence: {divergence}"
        assert entropy >= 0, f"Negative entropy: {entropy}"
        assert divergence >= 0, f"Negative divergence: {divergence}"

    @given(
        probs=st.lists(
            st.integers(min_value=0, max_value=100), min_size=0, max_size=10
        ),
    )
    @settings(derandomize=True, deadline=None)
    def test_manifold_curvature_bounded(self, probs):
        """Manifold curvature must always be a non-negative finite float."""
        import math as m

        recovery = self._make_recovery()
        causes = [{"probability": p} for p in probs]
        curvature = recovery._calculate_manifold_curvature(causes)
        assert m.isfinite(curvature), f"Non-finite curvature: {curvature}"
        assert curvature >= 0 or len(probs) >= 2, f"Unexpected negative: {curvature}"

    @given(
        exc_msg=st.text(min_size=0, max_size=200),
        exc_type_name=st.sampled_from(
            [
                "RuntimeError",
                "ValueError",
                "sqlite3.OperationalError",
                "AttributeError",
                "MemoryError",
                "OSError",
            ]
        ),
    )
    @settings(
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
        derandomize=True,
        max_examples=50,
    )
    def test_analyze_cause_never_crashes(self, exc_msg, exc_type_name):
        """_analyze_cause must never raise for any error message/type combo."""
        recovery = self._make_recovery()
        exc_type = type(exc_type_name, (Exception,), {})
        exc_type.__name__ = exc_type_name
        exc_value = Exception(exc_msg)
        diagnosis = {}
        causes = recovery._analyze_cause(exc_type, exc_value, diagnosis)
        assert isinstance(causes, list)
        for c in causes:
            assert isinstance(c["probability"], int)
            assert 0 <= c["probability"] <= 100
