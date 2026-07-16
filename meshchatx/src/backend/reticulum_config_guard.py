# SPDX-License-Identifier: 0BSD

"""Reticulum config file validation helpers for startup repair."""

from __future__ import annotations

import logging
import os
import shutil
import time

logger = logging.getLogger(__name__)


def reticulum_config_has_required_sections(config_path: str) -> bool:
    if not os.path.isfile(config_path):
        return False
    try:
        with open(config_path, encoding="utf-8") as handle:
            content = handle.read()
    except OSError:
        return False
    return "[reticulum]" in content and "[interfaces]" in content


def reticulum_config_is_parseable(config_path: str) -> bool:
    if not os.path.isfile(config_path):
        return False
    try:
        from RNS.vendor.configobj import ConfigObj

        cfg = ConfigObj(config_path)
    except Exception:
        return False
    return isinstance(cfg.get("reticulum"), dict) and isinstance(
        cfg.get("interfaces"),
        dict,
    )


def backup_reticulum_config_file(config_path: str) -> str | None:
    if not os.path.isfile(config_path):
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = f"{config_path}.corrupt.{stamp}"
    try:
        shutil.copy2(config_path, backup_path)
    except OSError as exc:
        logger.warning(
            "Failed to back up corrupt Reticulum config %s: %s",
            config_path,
            exc,
        )
        return None
    return backup_path


def repair_unparseable_reticulum_config(config_path: str, *, write_default) -> bool:
    """Back up and rewrite *config_path* when ConfigObj cannot parse it.

    *write_default* must be a callable accepting the config path and writing
    stock RNS defaults (``ReticulumMeshChat._write_rns_reticulum_default_config_file``).

    Returns True when the file was replaced.
    """
    if not reticulum_config_has_required_sections(config_path):
        return False
    if reticulum_config_is_parseable(config_path):
        return False

    backup_path = backup_reticulum_config_file(config_path)
    if backup_path:
        logger.warning(
            "Reticulum config at %s is unparseable; backed up to %s",
            config_path,
            backup_path,
        )
    else:
        logger.warning(
            "Reticulum config at %s is unparseable; rewriting without backup",
            config_path,
        )

    write_default(config_path)
    return True


def ensure_safe_reticulum_runtime_flags(config_path: str) -> bool:
    """Force runtime flags that keep MeshChatX alive when interfaces fail.

    Currently forces ``panic_on_interface_error = No`` so RNS does not call
    ``os._exit`` on interface faults.
    """
    from meshchatx.src.backend.rns_startup_recovery import (
        ensure_panic_on_interface_error_disabled,
    )

    return ensure_panic_on_interface_error_disabled(config_path)
