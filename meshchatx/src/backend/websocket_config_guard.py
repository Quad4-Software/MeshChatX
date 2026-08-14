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
