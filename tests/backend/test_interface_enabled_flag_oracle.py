# SPDX-License-Identifier: 0BSD

"""Oracle tests for interface enable/disable flag mutation."""

from __future__ import annotations

from meshchatx.src.backend.interface_enabled_flag import apply_interface_enabled_flag


def test_oracle_enable_writes_flag_when_neither_key_present():
    iface = {"type": "TCPClientInterface", "target_host": "127.0.0.1"}
    apply_interface_enabled_flag(iface, enabled=True)
    assert iface.get("interface_enabled") == "true"
    assert "enabled" not in iface or iface["enabled"] == "true"


def test_oracle_disable_writes_flag_when_neither_key_present():
    iface = {"type": "TCPClientInterface"}
    apply_interface_enabled_flag(iface, enabled=False)
    assert iface["interface_enabled"] == "false"


def test_oracle_enable_updates_both_legacy_keys():
    iface = {"enabled": "false", "interface_enabled": "false"}
    apply_interface_enabled_flag(iface, enabled=True)
    assert iface["enabled"] == "true"
    assert iface["interface_enabled"] == "true"


def test_oracle_disable_route_message_is_not_deleted():
    from pathlib import Path

    src = Path("meshchatx/src/backend/http/routes/interfaces.py").read_text(
        encoding="utf-8",
    )
    # The disable handler historically returned "Interface deleted".
    assert 'message": "Interface is now disabled"' in src
    disable_idx = src.index("async def reticulum_interfaces_disable")
    delete_idx = src.index("async def reticulum_interfaces_delete")
    disable_body = src[disable_idx:delete_idx]
    assert "Interface deleted" not in disable_body
