# SPDX-License-Identifier: 0BSD

"""Environment variable parsing helpers.

All reads of process environment should go through these helpers (or
path_utils for storage/path resolution) so parsing rules stay
consistent and the set of honoured variables stays greppable.
"""

from __future__ import annotations

# pyright: strict
import os
from pathlib import Path

_TRUE_VALUES = ("true", "1", "yes", "on")


def env_bool(env_name: str, default: bool = False) -> bool:
    val = os.environ.get(env_name)
    if val is None:
        return default
    return val.strip().lower() in _TRUE_VALUES


def env_str(env_name: str, default: str | None = None) -> str | None:
    val = os.environ.get(env_name)
    if val is None or val == "":
        return default
    return val


def env_int(env_name: str, default: int | None = None) -> int | None:
    val = os.environ.get(env_name)
    if val is None or val == "":
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def env_float(env_name: str, default: float | None = None) -> float | None:
    val = os.environ.get(env_name)
    if val is None or val == "":
        return default
    try:
        return float(val.strip())
    except ValueError:
        return default


def env_path(env_name: str, default: Path | None = None) -> Path | None:
    val = env_str(env_name)
    if val is None:
        return default
    return Path(val).expanduser()


def env_snapshot(env_names: tuple[str, ...] | list[str]) -> dict[str, str | None]:
    """Save the current values of a dynamic key set for later restore.

    For subprocess/temp env save-restore plumbing (for example TMPDIR
    around a media conversion), not for reading honoured config
    variables.
    """
    return {name: os.environ.get(name) for name in env_names}
