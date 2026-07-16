# SPDX-License-Identifier: 0BSD

"""List and create Reticulum management identity files.

These live under ``<reticulum_config_dir>/storage/identities/`` and are used by
rnstatus / rnpath remote queries (``-i``), rnx, and rnsh.
"""

from __future__ import annotations

import os
import re
from typing import Any

import RNS

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def identities_dir(reticulum_config_dir: str | None) -> str:
    """Return the RNS identities directory for a config root."""
    if isinstance(reticulum_config_dir, str) and reticulum_config_dir.strip():
        root = os.path.expanduser(reticulum_config_dir.strip())
    else:
        root = getattr(RNS.Reticulum, "configdir", None) or os.path.expanduser(
            "~/.reticulum",
        )
    return os.path.join(root, "storage", "identities")


def _safe_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not _SAFE_NAME_RE.match(cleaned):
        raise ValueError(
            "Identity name must be 1-64 characters: letters, digits, ., _, -",
        )
    return cleaned


def _identity_info(path: str, name: str) -> dict[str, Any] | None:
    try:
        identity = RNS.Identity.from_file(path)
    except Exception:
        return None
    if identity is None:
        return None
    try:
        identity_hash_raw = identity.hash
        if identity_hash_raw is None:
            return None
        identity_hash = bytes(identity_hash_raw).hex()
    except Exception:
        return None
    return {
        "name": name,
        "path": path,
        "hash": identity_hash,
    }


def list_management_identities(
    reticulum_config_dir: str | None,
) -> list[dict[str, Any]]:
    """List identity files under the RNS identities directory."""
    directory = identities_dir(reticulum_config_dir)
    if not os.path.isdir(directory):
        return []
    results: list[dict[str, Any]] = []
    try:
        entries = sorted(os.listdir(directory))
    except OSError:
        return []
    for entry in entries:
        path = os.path.join(directory, entry)
        if not os.path.isfile(path):
            continue
        info = _identity_info(path, entry)
        if info is not None:
            results.append(info)
    return results


def create_management_identity(
    reticulum_config_dir: str | None,
    name: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Generate a new RNS identity file under the identities directory."""
    cleaned = _safe_name(name)
    directory = identities_dir(reticulum_config_dir)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, cleaned)
    if os.path.exists(path) and not force:
        raise FileExistsError(f"Identity file already exists: {cleaned}")
    identity = RNS.Identity()
    identity.to_file(path)
    info = _identity_info(path, cleaned)
    if info is None:
        raise RuntimeError("Created identity file but failed to reload it")
    return info


def resolve_identity_path(
    reticulum_config_dir: str | None,
    identity_path: str | None = None,
    identity_name: str | None = None,
) -> str:
    """Resolve a management identity file path from path or short name."""
    if isinstance(identity_path, str) and identity_path.strip():
        path = os.path.expanduser(identity_path.strip())
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Identity file not found: {path}")
        return path
    if isinstance(identity_name, str) and identity_name.strip():
        cleaned = _safe_name(identity_name.strip())
        path = os.path.join(identities_dir(reticulum_config_dir), cleaned)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Identity file not found: {cleaned}")
        return path
    raise ValueError("identity_path or identity_name is required")
