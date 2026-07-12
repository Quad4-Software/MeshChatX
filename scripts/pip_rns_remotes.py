#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Shared remotes and helpers for optional pip-rns / rngit tooling."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PIP_RNS_CONFIG_DIR = REPO_ROOT / "scripts" / "pip-rns"
ALIASES_PATH = PIP_RNS_CONFIG_DIR / "aliases"

# Upstream markqvist rngit remotes (destination hash + group/repo).
DEFAULT_RNS_IDENTITY = "7649a50d84610232d1416b41d2896aff"
DEFAULT_GROUP = "reticulum"

DEFAULT_PACKAGE_ALIASES = {
    "rns": f"{DEFAULT_RNS_IDENTITY}/{DEFAULT_GROUP}/reticulum",
    "lxmf": f"{DEFAULT_RNS_IDENTITY}/{DEFAULT_GROUP}/lxmf",
    "lxst": f"{DEFAULT_RNS_IDENTITY}/{DEFAULT_GROUP}/lxst",
}

DEFAULT_WEBSITE_REMOTE = f"rns://{DEFAULT_RNS_IDENTITY}/{DEFAULT_GROUP}/website"

DEFAULT_INSTALL_PACKAGES = ("rns", "lxmf", "lxst")


def parse_aliases(path: Path | None = None) -> dict[str, str]:
    """Parse a pip-rns aliases file into ``name -> identity/group/repo``."""
    target = path or ALIASES_PATH
    result: dict[str, str] = {}
    if not target.is_file():
        return dict(DEFAULT_PACKAGE_ALIASES)
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name and value:
            result[name] = value
    return result


def remote_url(alias_or_path: str, aliases: dict[str, str] | None = None) -> str:
    """Return an ``rns://`` URL for an alias name or raw ``identity/group/repo``."""
    table = aliases if aliases is not None else parse_aliases()
    raw = table.get(alias_or_path, alias_or_path).strip()
    if raw.lower().startswith("rns://"):
        return raw
    return f"rns://{raw.lstrip('/')}"


def website_docs_source(aliases: dict[str, str] | None = None) -> str:
    """Preferred ``rns://`` source for the Reticulum website/manual repo."""
    table = aliases if aliases is not None else parse_aliases()
    if "website" in table:
        return remote_url("website", table)
    return DEFAULT_WEBSITE_REMOTE
