# SPDX-License-Identifier: 0BSD AND MIT


from meshchatx.src.backend.interface_editor import InterfaceEditor


def test_apply_fixed_mtu_rejects_below_minimum():
    details = {}
    message = InterfaceEditor.apply_fixed_mtu(details, {"fixed_mtu": 485})
    assert message is not None
    assert "500" in message
    assert "fixed_mtu" not in details


def test_apply_fixed_mtu_accepts_minimum():
    details = {}
    message = InterfaceEditor.apply_fixed_mtu(details, {"fixed_mtu": 500})
    assert message is None
    assert details["fixed_mtu"] == 500


def test_apply_fixed_mtu_clears_when_empty():
    details = {"fixed_mtu": 900}
    message = InterfaceEditor.apply_fixed_mtu(details, {"fixed_mtu": ""})
    assert message is None
    assert "fixed_mtu" not in details
