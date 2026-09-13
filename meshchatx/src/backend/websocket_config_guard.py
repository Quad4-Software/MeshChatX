# SPDX-License-Identifier: 0BSD

"""WebSocket guards for config updates and authenticated mutators.

Settings that change the HTTP security boundary must go through CSRF-protected
HTTP endpoints, not the unauthenticated config.set WebSocket message.

WebSocket upgrades also enforce a same-authority Origin check. Browsers always
send an Origin header on cross-site WebSocket handshakes, so requiring it to
match the request authority blocks cross-site hijacking of the local daemon
while non-browser clients without an Origin keep working.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from meshchatx.src.backend.constants import (
    WS_PUBLIC_TYPES,
    WS_RUNTIME_CONTROL_TYPES,
    WsInboundType,
)

logger = logging.getLogger(__name__)

WEBSOCKET_CONFIG_DENYLIST = frozenset(
    {
        "auth_enabled",
        "auth_password_hash",
        # Clearnet outbound kill-switch. Must use CSRF-protected HTTP PATCH.
        "privacy_mode_enabled",
    },
)

# Handled in websocket dispatch before WS_HANDLERS lookup.
WEBSOCKET_RUNTIME_CONTROL_TYPES = WS_RUNTIME_CONTROL_TYPES

WEBSOCKET_PUBLIC_TYPES = WS_PUBLIC_TYPES

WEBSOCKET_READ_TYPES = frozenset(
    {
        WsInboundType.NOMADNET_PAGE_ARCHIVES_GET,
        WsInboundType.NOMADNET_PAGE_ARCHIVE_LOAD,
        WsInboundType.LXMF_FORWARDING_RULES_GET,
        WsInboundType.KEYBOARD_SHORTCUTS_GET,
    },
)

WEBSOCKET_MUTATOR_TYPES = frozenset(
    {
        WsInboundType.CONFIG_SET,
        WsInboundType.KEYBOARD_SHORTCUTS_DELETE,
        WsInboundType.KEYBOARD_SHORTCUTS_SET,
        WsInboundType.LXM_GENERATE_PAPER_URI,
        WsInboundType.LXM_INGEST_URI,
        WsInboundType.LXMF_FORWARDING_RULE_ADD,
        WsInboundType.LXMF_FORWARDING_RULE_DELETE,
        WsInboundType.LXMF_FORWARDING_RULE_TOGGLE,
        WsInboundType.NOMADNET_DOWNLOAD_CANCEL,
        WsInboundType.NOMADNET_FILE_DOWNLOAD,
        WsInboundType.NOMADNET_PAGE_ARCHIVE_ADD,
        WsInboundType.NOMADNET_PAGE_ARCHIVE_FLUSH,
        WsInboundType.NOMADNET_PAGE_DOWNLOAD,
        WsInboundType.RNS_LINK_CLOSE,
        WsInboundType.RNS_LINK_IDENTIFY,
        WsInboundType.RNS_LINK_OPEN,
        WsInboundType.RNS_LINK_REQUEST,
        WsInboundType.RNS_LINK_SEND,
    },
)


def websocket_type_requires_auth(msg_type: str) -> bool:
    # Fail closed: only explicitly public types skip the session check.
    # New handlers land in the registry without touching this file, so an
    # unknown type must not silently run unauthenticated.
    if msg_type in WEBSOCKET_PUBLIC_TYPES:
        return False
    return True


def _authority_host_port(authority: str, default_port: int) -> tuple[str, int] | None:
    try:
        parsed = urlparse(f"//{authority.strip()}")
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return None
    if not host:
        return None
    return host, port if port is not None else default_port


def websocket_origin_allowed(request, trusted_proxy_cidrs: str | None = None) -> bool:
    """Return True when the WebSocket upgrade Origin matches the request authority.

    Requests without an Origin header are allowed so local non-browser tooling
    keeps working. Browsers always send Origin on cross-site handshakes, which
    is what makes this an effective cross-site hijacking defense. When the
    direct peer is a trusted reverse proxy, X-Forwarded-Host is accepted as
    the public authority.
    """
    origin = request.headers.get("Origin")
    if origin is None or not origin.strip():
        return True
    try:
        parsed = urlparse(origin.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.username or parsed.password:
            return False
        origin_port = parsed.port
    except ValueError:
        return False
    origin_host = (parsed.hostname or "").lower()
    if not origin_host:
        return False
    if origin_port is None:
        origin_port = 443 if parsed.scheme == "https" else 80

    default_port = 443 if request.scheme == "https" else 80
    candidates = [request.host]
    if trusted_proxy_cidrs:
        remote = (request.remote or "").strip()
        if remote:
            from meshchatx.src.backend.ip_allowlist import client_ip_allowed

            if client_ip_allowed(remote, trusted_proxy_cidrs):
                forwarded_host = request.headers.get("X-Forwarded-Host")
                if forwarded_host:
                    candidates.insert(0, forwarded_host.split(",")[0].strip())

    for authority in candidates:
        if not authority:
            continue
        parsed_authority = _authority_host_port(authority, default_port)
        if parsed_authority == (origin_host, origin_port):
            return True
    logger.warning(
        "Rejected WebSocket upgrade with mismatched Origin %r (Host %r)",
        origin,
        request.host,
    )
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
