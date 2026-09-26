# SPDX-License-Identifier: 0BSD
"""Redaction helpers for Reticulum config secrets over HTTP."""

from __future__ import annotations

from meshchatx.src.backend.app_security_settings import get_trusted_proxy_cidrs
from meshchatx.src.path_utils import request_client_ip

# Keys in the Reticulum config whose values are secrets. Served only to
# loopback clients or authenticated sessions; redacted otherwise so a LAN
# bind with auth disabled cannot leak shared-instance or interface keys.
SECRET_CONFIG_KEYS = {
    "rpc_key",
    "ifac_netkey",
    "networkname",
    "passphrase",
    "psk",
    "shared_instance_access",
}
REDACTED_SENTINEL = "<redacted>"


def _is_loopback_ip(ip: str) -> bool:
    import ipaddress

    try:
        return ipaddress.ip_address((ip or "").strip()).is_loopback
    except ValueError:
        return (ip or "").strip().lower() in ("localhost", "::1", "[::1]")


def request_may_receive_secrets(request, app) -> bool:
    """Decide whether the caller may see plaintext config secrets.

    Loopback clients always may; when auth is enabled the session check in
    auth middleware already ran, so reaching the handler means authenticated.
    Only an unauthenticated non-loopback caller (LAN bind + auth off) is denied.
    """
    if _is_loopback_ip(
        request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir))
    ):
        return True
    return bool(getattr(app, "auth_enabled", False))


def redact_config_secrets(content: str) -> str:
    out = []
    for line in content.splitlines():
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip().lower() if "=" in stripped else ""
        if key in SECRET_CONFIG_KEYS and not stripped.startswith(("#", ";")):
            indent = line[: len(line) - len(stripped)]
            out.append(f"{indent}{key} = {REDACTED_SENTINEL}")
        else:
            out.append(line)
    return "\n".join(out)


def restore_redacted_secrets(content: str, existing: str) -> str:
    """Restore real values for keys still holding REDACTED_SENTINEL.

    PUT round-trip safety: a body that still contains REDACTED_SENTINEL for a
    key keeps the value from the current file instead of writing the sentinel.
    """
    existing_values = {}
    for line in existing.splitlines():
        stripped = line.lstrip()
        if "=" not in stripped or stripped.startswith(("#", ";")):
            continue
        key, _, value = stripped.partition("=")
        key = key.strip().lower()
        if key in SECRET_CONFIG_KEYS:
            existing_values[key] = value.strip()

    out = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if "=" in stripped and not stripped.startswith(("#", ";")):
            key, _, value = stripped.partition("=")
            key_l = key.strip().lower()
            if key_l in SECRET_CONFIG_KEYS and value.strip() == REDACTED_SENTINEL:
                indent = line[: len(line) - len(stripped)]
                out.append(f"{indent}{key.strip()} = {existing_values.get(key_l, '')}")
                continue
        out.append(line)
    return "\n".join(out)
