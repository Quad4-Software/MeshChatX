# SPDX-License-Identifier: 0BSD

"""Process umask and one-time tightening of existing profile permissions."""

from __future__ import annotations

import os
import stat

_TIGHTEN_MARKER = ".perms-tightened-v1"
_UMASK_ENV_OPT_OUT = "MESHCHATX_NO_UMASK"


def apply_process_umask() -> None:
    """Set umask 0o077 for files this process creates, unless opted out."""
    if os.name == "nt":
        return
    if os.environ.get(_UMASK_ENV_OPT_OUT) in ("1", "true", "yes", "on"):
        return
    os.umask(0o077)


def _tighten_path(path: str) -> None:
    try:
        st = os.lstat(path)
    except OSError:
        return
    if stat.S_ISLNK(st.st_mode):
        return
    new_mode = stat.S_IMODE(st.st_mode) & ~0o077
    if new_mode == stat.S_IMODE(st.st_mode):
        return
    try:
        os.chmod(path, new_mode, follow_symlinks=False)
    except (OSError, NotImplementedError):
        try:
            os.chmod(path, new_mode)
        except OSError:
            pass


def _tighten_tree(root: str) -> None:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            _tighten_path(os.path.join(dirpath, name))
        for name in filenames:
            _tighten_path(os.path.join(dirpath, name))
    _tighten_path(root)


def _owned_by_current_uid(path: str) -> bool:
    try:
        return os.lstat(path).st_uid == os.getuid()
    except (OSError, AttributeError):
        return False


def tighten_existing_profile(
    storage_dir: str, reticulum_config_dir: str | None
) -> None:
    """One-time pass clearing group/other bits on an existing profile.

    Idempotent via a marker file in the storage dir. Never follows symlinks,
    never adds permission bits, and tolerates per-entry failures (foreign-owned
    bind mounts must not break startup). Skipped entirely on Windows.
    """
    if os.name == "nt" or not storage_dir:
        return
    marker = os.path.join(storage_dir, _TIGHTEN_MARKER)
    try:
        if os.path.exists(marker):
            return
    except OSError:
        return
    try:
        os.makedirs(storage_dir, exist_ok=True)
        _tighten_tree(storage_dir)
        if reticulum_config_dir:
            config_file = os.path.join(reticulum_config_dir, "config")
            storage_root = os.path.join(reticulum_config_dir, "storage")
            for candidate in (config_file, storage_root):
                if os.path.exists(candidate) and _owned_by_current_uid(candidate):
                    if os.path.isfile(candidate):
                        _tighten_path(candidate)
                    elif os.path.isdir(candidate):
                        _tighten_tree(candidate)
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write("1\n")
    except OSError:
        pass
