# SPDX-License-Identifier: 0BSD

"""WebSocket config update guards.

Settings that change the HTTP security boundary must go through CSRF-protected
HTTP endpoints, not the unauthenticated ``config.set`` WebSocket message.
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
