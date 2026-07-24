# SPDX-License-Identifier: 0BSD

"""Helpers for Reticulum interface config flag mutations."""

from __future__ import annotations


def apply_interface_enabled_flag(interface: dict, *, enabled: bool) -> None:
    """Set enabled/interface_enabled consistently, including missing-key configs.

    Older or hand-edited configs may omit both keys. Enable/disable must still
    write a flag so the next RNS reload honors the change.
    """
    if not isinstance(interface, dict):
        raise TypeError("interface must be a dict")
    value = "true" if enabled else "false"
    if "enabled" in interface:
        interface["enabled"] = value
    if "interface_enabled" in interface:
        interface["interface_enabled"] = value
    if "enabled" not in interface and "interface_enabled" not in interface:
        interface["interface_enabled"] = value
