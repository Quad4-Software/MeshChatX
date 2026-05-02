# SPDX-License-Identifier: 0BSD

"""Shared HTTP(S) URL validation for outbound client requests (e.g. LibreTranslate)."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import unquote, urlparse, urlunparse


class UnsafeOutboundUrlError(ValueError):
    """Raised when a URL is not permitted for server-side fetch."""


def normalize_loopback_http_service_base(url: str) -> str:
    """Return scheme://host:port with no path, query, or fragment.

    Only ``http``/``https`` to loopback hosts (127.0.0.1, localhost, ::1) are allowed.
    Userinfo (embedded credentials) is rejected.
    """
    if not url or not isinstance(url, str):
        msg = "URL must be a non-empty string"
        raise UnsafeOutboundUrlError(msg)

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        msg = "URL must use http or https"
        raise UnsafeOutboundUrlError(msg)

    netloc = parsed.netloc or ""
    if "@" in netloc:
        msg = "URL must not contain credentials"
        raise UnsafeOutboundUrlError(msg)

    host = parsed.hostname
    if host is None:
        msg = "URL must include a hostname"
        raise UnsafeOutboundUrlError(msg)

    host_norm = host.lower().strip("[]")
    if host_norm not in ("127.0.0.1", "localhost", "::1"):
        msg = "URL host must be 127.0.0.1, localhost, or ::1"
        raise UnsafeOutboundUrlError(msg)

    authority = netloc
    origin = urlunparse((parsed.scheme, authority, "", "", "", ""))
    return origin.rstrip("/")


_WS_CTRL = re.compile(r"[\x00-\x20\x7f]")


def normalize_libretranslate_http_service_base(url: str) -> str:
    """Return scheme://host:port with no path, query, or fragment.

    Accepts any HTTP(S) hostname or IP reachable from this process (remote LibreTranslate or
    public API). Embedded credentials are rejected; non-http(s) schemes are rejected.

    Literal IPv4 link-local targets (``169.254.0.0/16``) are rejected as a common SSRF/metadata
    path. Other private or loopback addresses are allowed so local servers and overlays (e.g. VPN
    mesh) continue to work.
    """
    if not url or not isinstance(url, str):
        msg = "URL must be a non-empty string"
        raise UnsafeOutboundUrlError(msg)

    trimmed = url.strip()
    if _WS_CTRL.search(trimmed):
        msg = "URL must not contain whitespace or control characters"
        raise UnsafeOutboundUrlError(msg)

    parsed = urlparse(trimmed)
    if parsed.scheme not in ("http", "https"):
        msg = "URL must use http or https"
        raise UnsafeOutboundUrlError(msg)

    netloc = parsed.netloc or ""
    if "@" in netloc:
        msg = "URL must not contain credentials"
        raise UnsafeOutboundUrlError(msg)

    host = parsed.hostname
    if host is None:
        msg = "URL must include a hostname"
        raise UnsafeOutboundUrlError(msg)

    host_decoded = unquote(host, errors="strict")
    if _WS_CTRL.search(host_decoded):
        msg = "URL must not contain whitespace or control characters"
        raise UnsafeOutboundUrlError(msg)

    host_for_ip_check = host_decoded.lower().strip("[]")
    try:
        addr = ipaddress.ip_address(host_for_ip_check)
    except ValueError:
        pass
    else:
        if addr.version == 4 and addr.is_link_local:
            msg = "URL must not target an IPv4 link-local address"
            raise UnsafeOutboundUrlError(msg)
        if addr.is_multicast or addr.is_unspecified:
            msg = "URL must not target a multicast or unspecified address"
            raise UnsafeOutboundUrlError(msg)
        if addr.is_reserved:
            msg = "URL must not target a reserved address"
            raise UnsafeOutboundUrlError(msg)

    authority = netloc
    origin = urlunparse((parsed.scheme, authority, "", "", "", ""))
    return origin.rstrip("/")
