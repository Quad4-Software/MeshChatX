# SPDX-License-Identifier: 0BSD

"""Typing protocol for the app object passed into route registrars.

Route modules receive the live ReticulumMeshChat instance as app.
This Protocol documents the attributes handlers commonly need. It is not
an alternate runtime type.
"""

from __future__ import annotations

from typing import Any, Protocol


class MeshChatApp(Protocol):
    """Minimal surface route and WS modules may rely on."""

    storage_dir: str
    auth_enabled: bool
    identity: Any
    config: Any
    database: Any
    current_context: Any
    _startup_stage: str

    def get_public_path(self, *parts: str) -> str: ...
