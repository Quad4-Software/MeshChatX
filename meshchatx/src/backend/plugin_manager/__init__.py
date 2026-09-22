# SPDX-License-Identifier: 0BSD
"""Plugin install and runtime management."""

from __future__ import annotations

from meshchatx.src.backend.plugin_guard import PluginSecurityError
from meshchatx.src.backend.plugin_manager.manager import (
    MINIMAL_PLUGIN_WAT,
    PluginManager,
)
from meshchatx.src.backend.plugin_manager.record import PluginRecord

__all__ = [
    "MINIMAL_PLUGIN_WAT",
    "PluginManager",
    "PluginRecord",
    "PluginSecurityError",
]
