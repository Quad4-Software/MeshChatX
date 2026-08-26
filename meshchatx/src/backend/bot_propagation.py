# SPDX-License-Identifier: 0BSD

"""Backward-compatible re-exports for bot LXMF propagation helpers."""

from meshchatx.src.backend.bot_lxmf_config import (
    load_bot_lxmf_config_sidecar,
    normalize_lxmf_destination_hash,
    resolve_effective_bot_lxmf_settings,
    resolve_host_lxmf_propagation_settings,
    write_bot_lxmf_config_sidecar,
)

resolve_bot_lxmf_propagation_settings = resolve_host_lxmf_propagation_settings


def propagation_settings_to_cli_args(settings: dict) -> list[str]:
    args: list[str] = []
    node = settings.get("propagation_node")
    if node:
        args.extend(["--propagation-node", node])
    if settings.get("autopeer_propagation"):
        args.append("--autopeer-propagation")
    if not settings.get("propagation_fallback_enabled", True):
        args.append("--no-propagation-fallback")
    return args


def propagation_settings_from_cli(
    propagation_node=None,
    autopeer_propagation=False,
    propagation_fallback_enabled=True,
) -> dict:
    settings = {
        "propagation_fallback_enabled": bool(propagation_fallback_enabled),
        "autopeer_propagation": bool(autopeer_propagation),
    }
    node = normalize_lxmf_destination_hash(propagation_node)
    if node:
        settings["propagation_node"] = node
        settings["autopeer_propagation"] = False
    return settings
