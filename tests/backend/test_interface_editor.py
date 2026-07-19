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


def test_normalize_rnode_txpower_integer():
    assert InterfaceEditor.normalize_rnode_txpower(7) == 7
    assert InterfaceEditor.normalize_rnode_txpower("14") == 14
    assert InterfaceEditor.normalize_rnode_txpower("7.0") == 7


def test_validate_rnode_txpower_accepts_reticulum_range():
    assert InterfaceEditor.validate_rnode_txpower(0) is None
    assert InterfaceEditor.validate_rnode_txpower(22) is None
    assert InterfaceEditor.validate_rnode_txpower(37) is None


def test_validate_rnode_txpower_rejects_out_of_range():
    assert InterfaceEditor.validate_rnode_txpower(-9) is not None
    assert InterfaceEditor.validate_rnode_txpower(38) is not None
    assert InterfaceEditor.validate_rnode_txpower("bad") is not None
    assert InterfaceEditor.validate_rnode_txpower(None) is not None


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


def test_normalize_interface_mode_aliases():
    assert InterfaceEditor.normalize_interface_mode("internal") == "internal"
    assert InterfaceEditor.normalize_interface_mode("GW") == "gateway"
    assert InterfaceEditor.normalize_interface_mode("ap") == "access_point"
    assert InterfaceEditor.normalize_interface_mode("evil") is None
    assert InterfaceEditor.normalize_interface_mode("") is None


def test_apply_interface_mode_rejects_unknown():
    details = {}
    err = InterfaceEditor.apply_interface_mode(details, {"mode": "not-a-mode"})
    assert err is not None
    assert "mode" not in details


def test_apply_interface_mode_canonicalizes():
    details = {}
    assert InterfaceEditor.apply_interface_mode(details, {"mode": "internal"}) is None
    assert details["mode"] == "internal"
    assert InterfaceEditor.apply_interface_mode(details, {"mode": "gw"}) is None
    assert details["mode"] == "gateway"


def test_apply_yes_no_option_recursive_prs():
    details = {}
    assert (
        InterfaceEditor.apply_yes_no_option(
            details, {"recursive_prs": True}, "recursive_prs"
        )
        is None
    )
    assert details["recursive_prs"] == "yes"
    assert (
        InterfaceEditor.apply_yes_no_option(
            details,
            {"announces_from_internal": False},
            "announces_from_internal",
        )
        is None
    )
    assert details["announces_from_internal"] == "no"


def test_validate_location_cmd_rejects_shell_metacharacters():
    assert InterfaceEditor.validate_location_cmd("/usr/bin/true") is None
    assert InterfaceEditor.validate_location_cmd("~/bin/gps.sh") is None
    assert InterfaceEditor.validate_location_cmd("relative/path") is not None
    assert InterfaceEditor.validate_location_cmd("/tmp/evil;rm -rf /") is not None
    assert InterfaceEditor.validate_location_cmd("/tmp/$(id)") is not None
    assert InterfaceEditor.validate_location_cmd("/tmp/../etc/passwd") is not None


def test_apply_location_cmd_normalizes_home():
    details = {}
    err = InterfaceEditor.apply_location_cmd(details, {"location_cmd": "~/gps-loc"})
    assert err is None
    assert details["location_cmd"].endswith("gps-loc")
    assert details["location_cmd"].startswith("/")


def test_sanitize_imported_rns_options_rejects_bad_mode():
    body = {"mode": "warehouse"}
    assert InterfaceEditor.sanitize_imported_rns_options(body) is not None


def test_sanitize_imported_rns_options_accepts_internal():
    body = {
        "mode": "internal",
        "recursive_prs": "yes",
        "announces_from_internal": "no",
    }
    assert InterfaceEditor.sanitize_imported_rns_options(body) is None
    assert body["mode"] == "internal"
    assert body["recursive_prs"] == "yes"
    assert body["announces_from_internal"] == "no"
