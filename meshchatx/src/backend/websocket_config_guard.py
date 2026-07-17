# SPDX-License-Identifier: 0BSD

"""WebSocket guards for config updates and authenticated mutators.

Settings that change the HTTP security boundary must go through CSRF-protected
HTTP endpoints, not the unauthenticated config.set WebSocket message.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

WEBSOCKET_CONFIG_DENYLIST = frozenset(
    {
        "auth_enabled",
        "auth_password_hash",
    },
)

WEBSOCKET_PUBLIC_TYPES = frozenset(
    {
        "ping",
    },
)

WEBSOCKET_READ_TYPES = frozenset(
    {
        "nomadnet.page.archives.get",
        "nomadnet.page.archive.load",
        "lxmf.forwarding.rules.get",
        "keyboard_shortcuts.get",
    },
)

WEBSOCKET_MUTATOR_TYPES = frozenset(
    {
        "config.set",
        "keyboard_shortcuts.delete",
        "keyboard_shortcuts.set",
        "lxm.generate_paper_uri",
        "lxm.ingest_uri",
        "lxmf.forwarding.rule.add",
        "lxmf.forwarding.rule.delete",
        "lxmf.forwarding.rule.toggle",
        "nomadnet.download.cancel",
        "nomadnet.file.download",
        "nomadnet.page.archive.add",
        "nomadnet.page.archive.flush",
        "nomadnet.page.download",
        "rns.link.close",
        "rns.link.identify",
        "rns.link.open",
        "rns.link.request",
        "rns.link.send",
    },
)


def websocket_type_requires_auth(msg_type: str) -> bool:
    if msg_type in WEBSOCKET_PUBLIC_TYPES or msg_type in WEBSOCKET_READ_TYPES:
        return False
    if msg_type in WEBSOCKET_MUTATOR_TYPES:
        return True
    return False


def sanitize_websocket_config_update(config: object) -> dict:
    """Return a copy of *config* with security-sensitive keys removed."""
    if not isinstance(config, dict):
        return {}

    sanitized = dict(config)
    removed = [key for key in WEBSOCKET_CONFIG_DENYLIST if key in sanitized]
    for key in removed:
        del sanitized[key]

    if removed:
        logger.warning(
            "Ignored security-sensitive config keys over WebSocket: %s",
            ", ".join(sorted(removed)),
        )

    return sanitized
