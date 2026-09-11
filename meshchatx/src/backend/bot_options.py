# SPDX-License-Identifier: 0BSD

"""Per-bot options that are not LXMFBot kwargs: icon appearance and custom commands.

Normalizers raise ValueError on hard-invalid input so HTTP callers can answer
400, and return None when the option is absent or cleared.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

_HEX_COLOUR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")
_ICON_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_COMMAND_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

_RUNTIME_SIDECAR_NAME = "meshchatx_bot_runtime.json"

_MAX_CUSTOM_COMMANDS = 64
_MAX_CUSTOM_RESPONSE_CHARS = 4000
_MAX_CUSTOM_WELCOME_CHARS = 4000


def normalize_hex_colour(value) -> str | None:
    """Return a normalized #rrggbb string or None when unset."""
    if value is None or value == "":
        return None
    raw = str(value).strip()
    if not _HEX_COLOUR_RE.match(raw):
        msg = "colour must be a 6 digit hex value"
        raise ValueError(msg)
    return "#" + raw.lstrip("#").lower()


def normalize_bot_icon(raw) -> dict | None:
    """Normalize a bot icon spec to {icon_name, fg_color, bg_color} or None."""
    if raw is None or raw == {} or raw is False:
        return None
    if not isinstance(raw, dict):
        msg = "icon must be an object"
        raise ValueError(msg)

    icon_name = raw.get("icon_name")
    if icon_name is None or str(icon_name).strip() == "":
        return None
    icon_name = str(icon_name).strip()
    if not _ICON_NAME_RE.match(icon_name):
        msg = "icon_name may only contain letters, digits, dashes and underscores"
        raise ValueError(msg)

    fg = normalize_hex_colour(raw.get("fg_color"))
    bg = normalize_hex_colour(raw.get("bg_color"))
    return {
        "icon_name": icon_name,
        "fg_color": fg or "#6b7280",
        "bg_color": bg or "#e5e7eb",
    }


def normalize_bot_custom(raw) -> dict | None:
    """Normalize custom bot config to {commands, welcome} or None."""
    if raw is None or raw == {}:
        return None
    if not isinstance(raw, dict):
        msg = "custom must be an object"
        raise ValueError(msg)

    commands = []
    raw_commands = raw.get("commands") or []
    if not isinstance(raw_commands, list):
        msg = "commands must be a list"
        raise ValueError(msg)
    if len(raw_commands) > _MAX_CUSTOM_COMMANDS:
        msg = f"at most {_MAX_CUSTOM_COMMANDS} custom commands"
        raise ValueError(msg)

    seen = set()
    for item in raw_commands:
        if not isinstance(item, dict):
            msg = "each command must be an object"
            raise ValueError(msg)
        name = str(item.get("name") or "").strip()
        if not _COMMAND_NAME_RE.match(name):
            msg = (
                "command names may only contain letters, digits, dashes and underscores"
            )
            raise ValueError(msg)
        lowered = name.lower()
        if lowered in seen:
            msg = f"duplicate command name: {name}"
            raise ValueError(msg)
        seen.add(lowered)
        response = item.get("response")
        if not isinstance(response, str) or not response.strip():
            msg = f"command {name} needs a response"
            raise ValueError(msg)
        response = response.strip()
        if len(response) > _MAX_CUSTOM_RESPONSE_CHARS:
            msg = f"command {name} response too long"
            raise ValueError(msg)
        entry = {"name": name, "response": response}
        description = item.get("description")
        if isinstance(description, str) and description.strip():
            entry["description"] = description.strip()[:200]
        commands.append(entry)

    welcome = raw.get("welcome")
    if welcome is not None:
        if not isinstance(welcome, str):
            msg = "welcome must be a string"
            raise ValueError(msg)
        welcome = welcome.strip()
        if not welcome:
            welcome = None
        elif len(welcome) > _MAX_CUSTOM_WELCOME_CHARS:
            msg = "welcome message too long"
            raise ValueError(msg)

    if not commands and welcome is None:
        return None
    out: dict[str, Any] = {"commands": commands}
    if welcome is not None:
        out["welcome"] = welcome
    return out


def bot_runtime_sidecar_path(storage_dir: str) -> str:
    return os.path.join(storage_dir, _RUNTIME_SIDECAR_NAME)


def write_bot_runtime_sidecar(storage_dir: str, payload: dict) -> str:
    from meshchatx.src.path_utils import atomic_write_text

    doc: dict[str, Any] = {}
    for key in ("icon", "custom"):
        if key in payload:
            doc[key] = payload[key]
    path = bot_runtime_sidecar_path(storage_dir)
    atomic_write_text(path, json.dumps(doc, indent=2) + "\n")
    return path


def load_bot_runtime_sidecar(path: str | None) -> dict:
    """Read the runtime sidecar, normalizing each section. Never raises."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}

    out: dict[str, Any] = {}
    if "icon" in raw:
        # Keep the key even when it normalizes to None: explicit null means
        # the user cleared the icon, absent means use the template default.
        try:
            out["icon"] = normalize_bot_icon(raw.get("icon"))
        except ValueError:
            out["icon"] = None
    try:
        custom = normalize_bot_custom(raw.get("custom"))
    except ValueError:
        custom = None
    if custom:
        out["custom"] = custom
    return out
