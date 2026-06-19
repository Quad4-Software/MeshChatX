# SPDX-License-Identifier: 0BSD

"""App-wide security settings persisted under the storage directory."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from meshchatx.src.backend.ip_allowlist import normalize_allowlist_text

_SETTINGS_FILENAME = "app_security.json"
_LOCK = threading.RLock()


def _settings_path(storage_dir: str) -> str:
    return os.path.join(storage_dir, _SETTINGS_FILENAME)


def _default_settings() -> dict[str, Any]:
    return {
        "web_ui_ip_allowlist": "",
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
    storage_dir: str, updates: dict[str, Any]
) -> dict[str, Any]:
    from meshchatx.src.backend.ip_allowlist import parse_allowlist_networks

    current = load_app_security_settings(storage_dir)
    if "web_ui_ip_allowlist" in updates:
        text = normalize_allowlist_text(updates.get("web_ui_ip_allowlist"))
        if text:
            parse_allowlist_networks(text)
        current["web_ui_ip_allowlist"] = text
    path = _settings_path(storage_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with _LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
            f.write("\n")
    return current


def get_web_ui_ip_allowlist(storage_dir: str) -> str:
    return normalize_allowlist_text(
        load_app_security_settings(storage_dir).get("web_ui_ip_allowlist"),
    )
