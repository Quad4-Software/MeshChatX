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
