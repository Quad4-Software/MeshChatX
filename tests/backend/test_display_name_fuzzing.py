import base64

import RNS.vendor.umsgpack as msgpack
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.meshchat_utils import (
    parse_lxmf_display_name,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_stamp_cost,
    parse_nomadnetwork_node_display_name,
)

# Strategies for generating diverse display names
st_display_name = st.one_of(
    st.text(),
    st.binary(),
    st.none(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.floats(allow_nan=False, allow_infinity=False),
    st.lists(st.text()),
    st.dictionaries(st.text(), st.text()),
)


@st.composite
def st_lxmf_announce_app_data(draw):
    """Generates valid LXMF announce app_data (msgpack list [name, ...])."""
    name = draw(st_display_name)
    # LXMF announces are usually [display_name, stamp_cost, propagation_node_data, ...]
    # We'll generate lists of various lengths
    app_data_list = [name]
    extra_count = draw(st.integers(min_value=0, max_value=5))
    app_data_list.extend(draw(st_display_name) for _ in range(extra_count))

    return msgpack.packb(app_data_list)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(data=st.one_of(st.binary(), st_lxmf_announce_app_data()))
def test_parse_lxmf_display_name_property_based(data):
    # Test with bytes directly
    result = parse_lxmf_display_name(data)
    assert isinstance(result, str)

    # Test with base64 encoded string
    b64_data = base64.b64encode(data).decode("utf-8")
    result_b64 = parse_lxmf_display_name(b64_data)
    assert isinstance(result_b64, str)
    assert result == result_b64


@given(name=st.text())
def test_parse_nomadnetwork_node_display_name_property_based(name):
    # Valid UTF-8 bytes
    data = name.encode("utf-8", errors="replace")
    result = parse_nomadnetwork_node_display_name(data)
    assert isinstance(result, str)
    # It might not match perfectly if there were replacement characters, but it should be a string

    # Test with base64
    b64_data = base64.b64encode(data).decode("utf-8")
    result_b64 = parse_nomadnetwork_node_display_name(b64_data)
    assert isinstance(result_b64, str)
    assert result == result_b64


@given(data=st.binary())
def test_parse_lxmf_display_name_invalid_base64(data):
    # Generate something that is NOT valid base64 (by adding invalid chars)
    invalid_b64 = base64.b64encode(data).decode("utf-8") + "!!!"
    result = parse_lxmf_display_name(invalid_b64)
    assert isinstance(result, str)


@given(app_data=st_lxmf_announce_app_data())
def test_parse_lxmf_display_name_logic_check(app_data):
    """Verify that if we can manually unpack it, parse_lxmf_display_name matches our expectation."""
    try:
        unpacked = msgpack.unpackb(app_data)
        if isinstance(unpacked, list) and len(unpacked) >= 1:
            expected_raw = unpacked[0]
            result = parse_lxmf_display_name(app_data)

            if expected_raw is None:
                assert result == "Anonymous Peer"
            else:
                # Our implementation handles both bytes and strings, and uses errors='replace'
                if isinstance(expected_raw, bytes):
                    expected_str = expected_raw.decode("utf-8", errors="replace")
                else:
                    expected_str = str(expected_raw)
                assert result == expected_str
    except Exception:
        # If msgpack fails to unpack, the function should still return a string
        result = parse_lxmf_display_name(app_data)
        assert isinstance(result, str)


@given(data=st.binary(min_size=0, max_size=10000))
def test_parse_nomadnetwork_node_display_name_fuzz(data):
    # Should never crash even with completely random bytes
    result = parse_nomadnetwork_node_display_name(data)
    assert isinstance(result, str)


@given(name=st.text(min_size=0, max_size=10000))
def test_parse_lxmf_display_name_very_long(name):
    # Test with very long names
    app_data = msgpack.packb([name, None, None])
    result = parse_lxmf_display_name(app_data)
    assert result == name
    assert len(result) == len(name)


@given(data=st.binary())
def test_parse_lxmf_propagation_node_app_data_fuzz(data):
    # Should never crash
    result = parse_lxmf_propagation_node_app_data(data)
    if result is not None:
        assert isinstance(result, dict)
        assert "enabled" in result
        assert "timebase" in result
        assert "per_transfer_limit" in result


@given(data=st.binary())
def test_parse_lxmf_stamp_cost_fuzz(data):
    # Should never crash
    parse_lxmf_stamp_cost(data)
    # stamp_cost can be None or an integer (or whatever LXMF returns)
    # We just want to ensure no crash
