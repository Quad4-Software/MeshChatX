# SPDX-License-Identifier: 0BSD

"""Per-bot LXMF settings with optional inheritance from the host identity."""

from __future__ import annotations

import contextlib
import re
from typing import Any

_LXMF_HASH_RE = re.compile(r"^[0-9a-f]{32}$")
_PROPAGATION_MODES = frozenset({"inherit", "manual", "autopeer", "none"})
_SIDECAR_NAME = "meshchatx_bot_lxmf_config.json"
_COMMAND_PREFIX_RE = re.compile(r"^\S{0,8}$")
_MAX_ADMINS = 64

# Boolean overrides that pass straight through to LXMFBot kwargs.
_BOOL_OVERRIDES = (
    "announce_enabled",
    "announce_immediately",
    "first_message_enabled",
    "signature_verification_enabled",
    "require_message_signatures",
    "require_stamps",
    "request_unknown_identities",
    "identity_pinning_enabled",
    "permissions_enabled",
    "lxmf_commands_enabled",
    "message_persistence_enabled",
)

# Integer overrides with inclusive (min, max) bounds.
_INT_OVERRIDES = {
    "rate_limit": (0, 1000),
    "cooldown": (0, 86400),
    "max_warnings": (0, 100),
    "warning_timeout": (0, 86400),
    "message_queue_size": (1, 10000),
    "autopeer_maxdepth": (0, 64),
}


def normalize_command_prefix(value) -> str | None:
    if value is None:
        return None
    prefix = str(value)
    if not _COMMAND_PREFIX_RE.match(prefix):
        return None
    return prefix


def normalize_admin_hashes(raw) -> list[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        return None
    out: list[str] = []
    for item in raw:
        h = normalize_lxmf_destination_hash(item)
        if h and h not in out:
            out.append(h)
        if len(out) >= _MAX_ADMINS:
            break
    return out


def normalize_lxmf_destination_hash(value) -> str | None:
    if not value:
        return None
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        h = value.hex()
    else:
        h = str(value).strip().lower()
        h = h.replace(" ", "").replace("<", "").replace(">", "")
    if len(h) != 32 or not _LXMF_HASH_RE.match(h):
        return None
    return h


def bot_lxmf_config_sidecar_path(storage_dir: str) -> str:
    import os

    return os.path.join(storage_dir, _SIDECAR_NAME)


def resolve_host_lxmf_propagation_settings(config_manager) -> dict:
    fallback_enabled = True
    propagation_node = None
    autopeer_propagation = False

    if config_manager is not None:
        with contextlib.suppress(Exception):
            fallback_enabled = bool(
                config_manager.auto_send_failed_messages_to_propagation_node.get(),
            )
        with contextlib.suppress(Exception):
            raw = config_manager.lxmf_preferred_propagation_node_destination_hash.get()
            propagation_node = normalize_lxmf_destination_hash(raw)
        if propagation_node is None:
            with contextlib.suppress(Exception):
                autopeer_propagation = bool(
                    config_manager.lxmf_preferred_propagation_node_auto_select.get(),
                )

    settings: dict[str, Any] = {
        "propagation_fallback_enabled": fallback_enabled,
        "autopeer_propagation": autopeer_propagation,
    }
    if propagation_node:
        settings["propagation_node"] = propagation_node
    return settings


def normalize_bot_lxmf_overrides(raw) -> dict:
    if not isinstance(raw, dict):
        return {}

    out: dict[str, Any] = {}
    mode = raw.get("propagation_mode")
    if mode is not None:
        mode = str(mode).strip().lower()
        if mode in _PROPAGATION_MODES and mode != "inherit":
            out["propagation_mode"] = mode

    node = normalize_lxmf_destination_hash(raw.get("propagation_node"))
    if node:
        out["propagation_node"] = node

    fallback = raw.get("propagation_fallback_enabled")
    if fallback is not None:
        out["propagation_fallback_enabled"] = bool(fallback)

    retries = raw.get("direct_delivery_retries")
    if retries is not None and retries != "":
        try:
            parsed = int(retries)
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None and 0 <= parsed <= 32:
            out["direct_delivery_retries"] = parsed

    opportunistic = raw.get("opportunistic_sending")
    if opportunistic is not None:
        out["opportunistic_sending"] = bool(opportunistic)

    announce = raw.get("announce_interval_seconds")
    if announce is None:
        announce = raw.get("announce")
    if announce is not None and announce != "":
        try:
            parsed = int(announce)
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None and 30 <= parsed <= 86400:
            out["announce_interval_seconds"] = parsed

    stamp_cost = raw.get("stamp_cost")
    if stamp_cost is not None and stamp_cost != "":
        try:
            parsed = int(stamp_cost)
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None and parsed >= 0:
            out["stamp_cost"] = parsed

    for key in _BOOL_OVERRIDES:
        value = raw.get(key)
        if value is not None:
            out[key] = bool(value)

    for key, (low, high) in _INT_OVERRIDES.items():
        value = raw.get(key)
        if value is None or value == "":
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if low <= parsed <= high:
            out[key] = parsed

    prefix = normalize_command_prefix(raw.get("command_prefix"))
    if prefix is not None:
        out["command_prefix"] = prefix

    admins = normalize_admin_hashes(raw.get("admins"))
    if admins:
        out["admins"] = admins

    if out.get("propagation_mode") == "manual" and "propagation_node" not in out:
        out.pop("propagation_mode", None)

    if out.get("propagation_mode") in ("autopeer", "none"):
        out.pop("propagation_node", None)

    return out


def validate_bot_lxmf_patch(patch: dict | None) -> None:
    if not patch:
        return
    mode = patch.get("propagation_mode")
    if mode == "manual" and not normalize_lxmf_destination_hash(
        patch.get("propagation_node"),
    ):
        msg = "propagation_node is required for manual propagation mode"
        raise ValueError(msg)


def merge_bot_lxmf_overrides(stored: dict | None, patch: dict | None) -> dict:
    base = dict(normalize_bot_lxmf_overrides(stored or {}))
    if not patch:
        return base

    if patch.get("propagation_mode") == "inherit":
        base.pop("propagation_mode", None)
        base.pop("propagation_node", None)

    mode = patch.get("propagation_mode")
    if mode in ("autopeer", "none"):
        base.pop("propagation_node", None)

    clear_keys = (
        "propagation_node",
        "propagation_fallback_enabled",
        "direct_delivery_retries",
        "opportunistic_sending",
        "announce_interval_seconds",
        "stamp_cost",
        "command_prefix",
        "admins",
        *_BOOL_OVERRIDES,
        *_INT_OVERRIDES,
    )
    for key in clear_keys:
        if key in patch and patch[key] in (None, ""):
            base.pop(key, None)
        elif key == "admins" and isinstance(patch.get(key), list) and not patch[key]:
            base.pop(key, None)

    incoming = normalize_bot_lxmf_overrides(patch)
    base.update(incoming)
    return normalize_bot_lxmf_overrides(base)


def resolve_effective_bot_lxmf_settings(
    config_manager,
    bot_entry: dict | None,
) -> dict:
    """Return keyword args for LXMFBot after host inheritance and bot overrides."""
    host_prop = resolve_host_lxmf_propagation_settings(config_manager)
    overrides = normalize_bot_lxmf_overrides((bot_entry or {}).get("lxmf_config"))

    propagation_fallback_enabled = host_prop.get("propagation_fallback_enabled", True)
    if "propagation_fallback_enabled" in overrides:
        propagation_fallback_enabled = overrides["propagation_fallback_enabled"]

    propagation_node = host_prop.get("propagation_node")
    autopeer_propagation = host_prop.get("autopeer_propagation", False)
    mode = overrides.get("propagation_mode", "inherit")
    if mode == "manual":
        propagation_node = overrides.get("propagation_node")
        autopeer_propagation = False
    elif mode == "autopeer":
        propagation_node = None
        autopeer_propagation = True
    elif mode == "none":
        propagation_node = None
        autopeer_propagation = False
    elif overrides.get("propagation_node"):
        propagation_node = overrides["propagation_node"]
        autopeer_propagation = False

    settings: dict[str, Any] = {
        "propagation_fallback_enabled": propagation_fallback_enabled,
        "autopeer_propagation": autopeer_propagation,
    }
    if propagation_node:
        settings["propagation_node"] = propagation_node

    if "direct_delivery_retries" in overrides:
        settings["direct_delivery_retries"] = overrides["direct_delivery_retries"]
    if "opportunistic_sending" in overrides:
        settings["opportunistic_sending"] = overrides["opportunistic_sending"]
    if "announce_interval_seconds" in overrides:
        settings["announce"] = overrides["announce_interval_seconds"]
    if "stamp_cost" in overrides:
        settings["stamp_cost"] = overrides["stamp_cost"]

    for key in _BOOL_OVERRIDES:
        if key in overrides:
            settings[key] = overrides[key]
    for key in _INT_OVERRIDES:
        if key in overrides:
            settings[key] = overrides[key]
    if "command_prefix" in overrides:
        settings["command_prefix"] = overrides["command_prefix"]
    if "admins" in overrides:
        settings["admins"] = list(overrides["admins"])

    return settings


def describe_bot_lxmf_config(
    config_manager,
    bot_entry: dict | None,
) -> dict:
    overrides = normalize_bot_lxmf_overrides((bot_entry or {}).get("lxmf_config"))
    effective = resolve_effective_bot_lxmf_settings(config_manager, bot_entry)
    host_prop = resolve_host_lxmf_propagation_settings(config_manager)
    return {
        "lxmf_config": overrides,
        "effective_lxmf_config": effective,
        "host_lxmf_propagation": host_prop,
    }


def write_bot_lxmf_config_sidecar(storage_dir: str, settings: dict) -> str:
    from meshchatx.src.json_store import save_json

    path = bot_lxmf_config_sidecar_path(storage_dir)
    save_json(path, settings, indent=2)
    return path


def load_bot_lxmf_config_sidecar(path: str | None) -> dict:
    if not path:
        return {}
    from meshchatx.src.json_store import load_json

    raw = load_json(path, expect=dict)
    if raw is None:
        return {}

    settings: dict[str, Any] = {}
    if "propagation_fallback_enabled" in raw:
        settings["propagation_fallback_enabled"] = bool(
            raw["propagation_fallback_enabled"],
        )
    if raw.get("autopeer_propagation"):
        settings["autopeer_propagation"] = True
    node = normalize_lxmf_destination_hash(raw.get("propagation_node"))
    if node:
        settings["propagation_node"] = node
        settings["autopeer_propagation"] = False
    if "direct_delivery_retries" in raw:
        try:
            retries = int(raw["direct_delivery_retries"])
        except (TypeError, ValueError):
            retries = None
        if retries is not None and 0 <= retries <= 32:
            settings["direct_delivery_retries"] = retries
    if "opportunistic_sending" in raw:
        settings["opportunistic_sending"] = bool(raw["opportunistic_sending"])
    announce = raw.get("announce", raw.get("announce_interval_seconds"))
    if announce is not None:
        try:
            parsed = int(announce)
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None and 30 <= parsed <= 86400:
            settings["announce"] = parsed
    if "stamp_cost" in raw:
        try:
            parsed = int(raw["stamp_cost"])
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None and parsed >= 0:
            settings["stamp_cost"] = parsed

    for key in _BOOL_OVERRIDES:
        if key in raw:
            settings[key] = bool(raw[key])
    for key, (low, high) in _INT_OVERRIDES.items():
        if key not in raw:
            continue
        try:
            parsed = int(raw[key])
        except (TypeError, ValueError):
            continue
        if low <= parsed <= high:
            settings[key] = parsed
    prefix = normalize_command_prefix(raw.get("command_prefix"))
    if prefix is not None:
        settings["command_prefix"] = prefix
    admins = normalize_admin_hashes(raw.get("admins"))
    if admins:
        settings["admins"] = admins
    return settings
