# SPDX-License-Identifier: 0BSD

"""Shared HTTP(S) URL validation for outbound client requests (e.g. LibreTranslate)."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


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

    # Rebuild origin only (LibreTranslate mounts at /languages, /translate, etc.)
    authority = netloc
    origin = urlunparse((parsed.scheme, authority, "", "", "", ""))
    return origin.rstrip("/")
