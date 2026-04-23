# SPDX-License-Identifier: 0BSD

"""Property tests for Reticulum-style interface config parsing."""

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser


@settings(max_examples=150, deadline=None)
@given(text=st.text(max_size=8000))
def test_interface_config_parse_never_raises(text):
    result = InterfaceConfigParser.parse(text)
    assert isinstance(result, list)
    for iface in result:
        assert isinstance(iface, dict)
        assert "name" in iface
        assert isinstance(iface["name"], str)


@settings(max_examples=120, deadline=None)
@given(lines=st.lists(st.text(max_size=400), max_size=120))
def test_interface_config_parse_joined_lines_never_raises(lines):
    text = "\n".join(lines)
    result = InterfaceConfigParser.parse(text)
    assert isinstance(result, list)
    for iface in result:
        assert isinstance(iface, dict)
        assert "name" in iface
