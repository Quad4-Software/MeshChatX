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
