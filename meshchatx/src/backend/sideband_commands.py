# SPDX-License-Identifier: 0BSD

"""LXMF sense / telemetry command opcodes used by MeshChatX.

Numeric values match the Sideband sense command wire set so peers remain
interoperable. This module is Quad4-authored and does not copy Sideband source.
"""

from __future__ import annotations


class SidebandCommands:
    """Opcode constants for LXMF sense-style commands."""

    PLUGIN_COMMAND = 0x00
    TELEMETRY_REQUEST = 0x01
    PING = 0x02
    ECHO = 0x03
    SIGNAL_REPORT = 0x04
