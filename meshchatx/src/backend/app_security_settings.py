# SPDX-License-Identifier: 0BSD

"""App-wide security settings persisted under the storage directory."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from meshchatx.src.backend.ip_allowlist import normalize_allowlist_text
from meshchatx.src.path_utils import atomic_write_text

_SETTINGS_FILENAME = "app_security.json"
_LOCK = threading.RLock()


def _settings_path(storage_dir: str) -> str:
    return os.path.join(storage_dir, _SETTINGS_FILENAME)


def _default_settings() -> dict[str, Any]:
    return {
        "web_ui_ip_allowlist": "",
        "trusted_proxy_cidrs": "",
    }


def load_app_security_settings(storage_dir: str) -> dict[str, Any]:
    path = _settings_path(storage_dir)
    with _LOCK:
        if not os.path.isfile(path):
            return _default_settings()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return _default_settings()
        if not isinstance(data, dict):
            return _default_settings()
        merged = _default_settings()
        merged.update(data)
        return merged


def save_app_security_settings(
    storage_dir: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    from meshchatx.src.backend.ip_allowlist import parse_allowlist_networks

    current = load_app_security_settings(storage_dir)
    if "web_ui_ip_allowlist" in updates:
        text = normalize_allowlist_text(updates.get("web_ui_ip_allowlist"))
        if text:
            parse_allowlist_networks(text)
        current["web_ui_ip_allowlist"] = text
    if "trusted_proxy_cidrs" in updates:
        text = normalize_allowlist_text(updates.get("trusted_proxy_cidrs"))
        if text:
            parse_allowlist_networks(text)
        current["trusted_proxy_cidrs"] = text
    path = _settings_path(storage_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with _LOCK:
        atomic_write_text(path, json.dumps(current, indent=2) + "\n")
    return current


def get_web_ui_ip_allowlist(storage_dir: str) -> str:
    return normalize_allowlist_text(
        load_app_security_settings(storage_dir).get("web_ui_ip_allowlist"),
    )


def get_trusted_proxy_cidrs(storage_dir: str) -> str:
    """CIDRs allowed to supply X-Forwarded-For (env overrides file settings)."""
    env = normalize_allowlist_text(os.environ.get("MESHCHAT_TRUSTED_PROXIES"))
    if env:
        return env
    return normalize_allowlist_text(
        load_app_security_settings(storage_dir).get("trusted_proxy_cidrs"),
    )
