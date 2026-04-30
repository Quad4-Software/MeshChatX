# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.interface_editor import InterfaceEditor


def test_update_value_add():
    details = {"type": "TCPClientInterface"}
    InterfaceEditor.update_value(details, {"host": "1.2.3.4"}, "host")
    assert details["host"] == "1.2.3.4"


def test_update_value_update():
    details = {"host": "1.2.3.4"}
    InterfaceEditor.update_value(details, {"host": "8.8.8.8"}, "host")
    assert details["host"] == "8.8.8.8"


def test_update_value_remove_on_none():
    details = {"host": "1.2.3.4"}
    InterfaceEditor.update_value(details, {"host": None}, "host")
    assert "host" not in details


def test_update_value_remove_on_empty_string():
    details = {"host": "1.2.3.4"}
    InterfaceEditor.update_value(details, {"host": ""}, "host")
    assert "host" not in details


def test_coerce_rnode_frequency_hz_integer_hz():
    assert InterfaceEditor.coerce_rnode_frequency_hz(868825000) == 868825000
    assert InterfaceEditor.coerce_rnode_frequency_hz("868825000") == 868825000


def test_coerce_rnode_frequency_hz_mhz_decimal():
    assert InterfaceEditor.coerce_rnode_frequency_hz(868.825) == 868825000
    assert InterfaceEditor.coerce_rnode_frequency_hz("868.825000000") == 868825000
    assert InterfaceEditor.coerce_rnode_frequency_hz("868.825000000 MHz") == 868825000


def test_coerce_rnode_frequency_hz_integer_mhz():
    assert InterfaceEditor.coerce_rnode_frequency_hz(868) == 868000000


def test_coerce_rnode_frequency_hz_leaves_midrange_hz():
    assert InterfaceEditor.coerce_rnode_frequency_hz(125000) == 125000


def test_normalize_rnode_tcp_port_host_only():
    assert (
        InterfaceEditor.normalize_rnode_tcp_port("tcp://10.0.0.5") == "tcp://10.0.0.5"
    )


def test_normalize_rnode_tcp_port_strips_legacy_ipv4_port():
    assert (
        InterfaceEditor.normalize_rnode_tcp_port("tcp://10.0.0.5:7633")
        == "tcp://10.0.0.5"
    )


def test_normalize_rnode_tcp_port_strips_trailing_colons():
    assert (
        InterfaceEditor.normalize_rnode_tcp_port("tcp://10.0.0.5:") == "tcp://10.0.0.5"
    )


def test_normalize_rnode_tcp_port_bracket_ipv6_with_port():
    assert (
        InterfaceEditor.normalize_rnode_tcp_port("tcp://[2001:db8::1]:7633")
        == "tcp://[2001:db8::1]"
    )


def test_normalize_rnode_tcp_port_non_tcp_unchanged():
    assert InterfaceEditor.normalize_rnode_tcp_port("/dev/ttyUSB0") == "/dev/ttyUSB0"
