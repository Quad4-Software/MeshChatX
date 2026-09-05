# SPDX-License-Identifier: 0BSD

"""Shared HTTP(S) URL validation for outbound client requests (e.g. LibreTranslate)."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import unquote, urlparse, urlunparse


class UnsafeOutboundUrlError(ValueError):
    """Raised when a URL is not permitted for server-side fetch."""


def normalize_loopback_http_service_base(url: str) -> str:
    """Return scheme://host:port with no path, query, or fragment.

    Only http/https to loopback hosts (127.0.0.1, localhost, ::1) are allowed.
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


def _coerce_host_to_ip(
    host: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse dotted/colon IPs plus decimal and 0x hex IPv4 host forms browsers accept."""
    if not host:
        return None
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    # Integer / hex IPv4 (e.g. 2852039166, 0xa9fea9fe -> 169.254.169.254).
    try:
        if host.startswith("0x") or host.startswith("0X"):
            return ipaddress.IPv4Address(int(host, 16))
        if host.isdigit():
            return ipaddress.IPv4Address(int(host))
    except (ValueError, OverflowError):
        return None
    return None


def _reject_forbidden_outbound_ip(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> None:
    """Raise when addr is link-local, multicast, unspecified, or reserved."""
    effective = addr.ipv4_mapped if getattr(addr, "ipv4_mapped", None) else addr
    if effective.is_link_local or addr.is_link_local:
        msg = "URL must not target a link-local address"
        raise UnsafeOutboundUrlError(msg)
    if (
        effective.is_multicast
        or effective.is_unspecified
        or addr.is_multicast
        or addr.is_unspecified
    ):
        msg = "URL must not target a multicast or unspecified address"
        raise UnsafeOutboundUrlError(msg)
    if effective.is_reserved or addr.is_reserved:
        msg = "URL must not target a reserved address"
        raise UnsafeOutboundUrlError(msg)


def _reject_hostname_resolved_forbidden(host: str) -> None:
    """Best-effort DNS check: reject hostnames that currently resolve to forbidden IPs.

    Does not defeat DNS rebinding between check and connect. Unresolvable names are
    left to the later HTTP client (same as before).
    """
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            resolved = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        _reject_forbidden_outbound_ip(resolved)


def normalize_libretranslate_http_service_base(url: str) -> str:
    """Return scheme://host:port with no path, query, or fragment.

    Accepts any HTTP(S) hostname or IP reachable from this process (remote LibreTranslate or
    public API). Embedded credentials are rejected; non-http(s) schemes are rejected.

    Literal IPv4 link-local targets (169.254.0.0/16) are rejected as a common SSRF/metadata
    path, including decimal and hex encodings of those addresses. Hostnames that resolve to
    those addresses are also rejected at normalize time. Other private or loopback
    addresses are allowed so local servers and overlays (e.g. VPN mesh) continue to work.
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
    addr = _coerce_host_to_ip(host_for_ip_check)
    if addr is not None:
        _reject_forbidden_outbound_ip(addr)
    else:
        _reject_hostname_resolved_forbidden(host_decoded)

    authority = netloc
    origin = urlunparse((parsed.scheme, authority, "", "", "", ""))
    return origin.rstrip("/")
