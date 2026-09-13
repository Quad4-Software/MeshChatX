# SPDX-License-Identifier: 0BSD

"""Plugin install record."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginRecord:
    id: str
    version: str
    manifest: dict[str, Any]
    enabled: bool
    install_path: str
    auto_disabled_reason: str | None = None
    granted_permissions: list[str] | None = None
    announce_handlers: list[Any] = field(default_factory=list)
    error_count: int = 0
    last_error_at: float = 0.0
    integrity_hash: str | None = None
    tampered: bool = False
    signature: dict[str, Any] | None = None
