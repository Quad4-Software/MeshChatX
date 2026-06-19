# SPDX-License-Identifier: 0BSD

"""Privacy mode: block outbound HTTP/HTTPS from the backend and tighten CSP."""

from __future__ import annotations


class OutboundHttpBlockedError(RuntimeError):
    """Raised when privacy mode blocks a server-side HTTP request."""


def privacy_mode_enabled(config) -> bool:
    if config is None:
        return False
    getter = getattr(config, "privacy_mode_enabled", None)
    if getter is None:
        return False
    return bool(getter.get())


def ensure_outbound_http_allowed(config, *, feature: str = "outbound HTTP") -> None:
    if privacy_mode_enabled(config):
        msg = f"Privacy mode is enabled; {feature} is blocked"
        raise OutboundHttpBlockedError(msg)


def csp_allows_external_sources(config) -> bool:
    return not privacy_mode_enabled(config)
