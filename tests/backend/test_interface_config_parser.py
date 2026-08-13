# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser


def test_parse_simple_interface():
    config_text = """
[[Test Interface]]
  type = TCPClientInterface
  enabled = yes
  target_host = 127.0.0.1
  target_port = 4242
"""
    interfaces = InterfaceConfigParser.parse(config_text)
    assert len(interfaces) == 1
    assert interfaces[0]["name"] == "Test Interface"
    assert interfaces[0]["type"] == "TCPClientInterface"
    assert interfaces[0]["enabled"] == "yes"


def test_parse_multiple_interfaces():
    config_text = """
[[Interface One]]
  type = RNodeInterface
[[Interface Two]]
  type = TCPClientInterface
"""
    interfaces = InterfaceConfigParser.parse(config_text)
    assert len(interfaces) == 2
    assert interfaces[0]["name"] == "Interface One"
    assert interfaces[1]["name"] == "Interface Two"


def test_parse_best_effort_on_failure():
    # Invalid config that should trigger best-effort parsing
    config_text = """
[[Broken Interface]
  type = something
[[Fixed Interface]]
  type = fixed
"""
    interfaces = InterfaceConfigParser.parse(config_text)
    assert len(interfaces) >= 1
    names = [i["name"] for i in interfaces]
    assert "Fixed Interface" in names


def test_parse_dotted_hostname_section_name():
    config_text = """
[[artyom.ddns.net]]
  type = TCPClientInterface
  interface_enabled = True
  target_host = 10.100.11.12
  target_port = 4242
  name = artyom.ddns.net
[[Catz-Node (TCP)]]
  type = TCPClientInterface
"""
    interfaces = InterfaceConfigParser.parse(config_text)
    names = [i["name"] for i in interfaces]
    assert "artyom.ddns.net" in names
    assert "Catz-Node (TCP)" in names
    dotted = next(i for i in interfaces if i["name"] == "artyom.ddns.net")
    assert dotted["type"] == "TCPClientInterface"
    assert dotted["target_host"] == "10.100.11.12"


def test_parse_subsections():
    config_text = """
[[Interface With Sub]]
  type = AutoInterface
  [[[sub_config]]]
    key = value
"""
    interfaces = InterfaceConfigParser.parse(config_text)
    assert len(interfaces) == 1
    assert "sub_config" in interfaces[0]
    assert interfaces[0]["sub_config"]["key"] == "value"
