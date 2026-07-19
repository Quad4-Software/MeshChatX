"""Config loading for RNS FileSync (rngit-style ConfigObj)."""

from __future__ import annotations

import os
from typing import Any

from RNS.vendor.configobj import ConfigObj

DEFAULT_CONFIG_DIR = os.path.expanduser("~/.rns_filesync")

DEFAULT_CONFIG = """# RNS FileSync config
# Similar layout to rngit (~/.rngit/config).

[filesync]

# Automatic announce interval in seconds.
announce_interval = 300

# Optional default sync directory (overridden by -d).
# directory = ~/shared

# Identity name stored under this config dir.
identity = rns_filesync

# Comma-separated peer identity hashes to connect on start.
# peers = 9710b86ba12c42d1d8f30f74fe509286

# Deny these identity hashes even if access rules would allow them.
# blocked_identities = d31aeea49873006f13b3415520666a4e

[aliases]
# alice = d09285e660cfe27cee6d9a0beb58b7e0

[access]
# Access rules for the sync directory (comma-separated).
# Format matches rngit: permission:target
#
# Permissions:
#   r   = read
#   w   = write
#   d   = delete
#   rw  = read/write
#   rwd = read/write/delete
#   adm = admin (all permissions)
#
# Targets: identity hash, alias name, all, or none.
#
# By default there are no permissions: peers cannot sync
# until you add rules here and/or a sidecar .allowed file.
#
# sync = r:all, w:9710b86ba12c42d1d8f30f74fe509286, d:9710b86ba12c42d1d8f30f74fe509286

[logging]
loglevel = 4
"""


def resolve_config_dir(config_dir: str | None = None) -> str:
    if config_dir:
        return os.path.realpath(os.path.expanduser(config_dir))
    if os.path.isfile("/etc/rns_filesync/config"):
        return "/etc/rns_filesync"
    return DEFAULT_CONFIG_DIR


def ensure_config(config_dir: str | None = None) -> str:
    """Ensure config directory and default config file exist. Return config dir."""
    path = resolve_config_dir(config_dir)
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "identities"), exist_ok=True)
    config_path = os.path.join(path, "config")
    if not os.path.isfile(config_path):
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write(DEFAULT_CONFIG)
    return path


def load_config(config_dir: str | None = None) -> tuple[str, ConfigObj]:
    """Load ConfigObj from config dir, creating defaults if needed."""
    path = ensure_config(config_dir)
    config_path = os.path.join(path, "config")
    config = ConfigObj(config_path)
    return path, config


def config_get(config: ConfigObj, section: str, key: str, default: Any = None) -> Any:
    try:
        section_obj = config.get(section) or {}
        if key in section_obj and section_obj[key] not in (None, ""):
            return section_obj[key]
    except Exception:
        pass
    return default


def parse_csv_hashes(value: str | list | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value).split(",")
    return [p.strip().lower().replace(":", "") for p in parts if p and str(p).strip()]


def allowed_sidecar_paths(sync_directory: str) -> list[str]:
    """Candidate .allowed paths for a sync directory (rngit-style sidecars)."""
    sync_directory = os.path.realpath(os.path.expanduser(sync_directory))
    parent = os.path.dirname(sync_directory.rstrip(os.sep))
    base = os.path.basename(sync_directory.rstrip(os.sep))
    return [
        os.path.join(sync_directory, ".allowed"),
        os.path.join(parent, f"{base}.allowed"),
        sync_directory.rstrip(os.sep) + ".allowed",
    ]
