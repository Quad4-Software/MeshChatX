# SPDX-License-Identifier: 0BSD
"""Baked build metadata (git commit and channel).

Defaults keep source checkouts and tests working without a bake step.
Builds run scripts/bake_build_meta.js which writes _build_meta_baked.py
(gitignored). Packaging includes that overlay when present.
"""

from __future__ import annotations

GIT_COMMIT = ""
GIT_COMMIT_SHORT = ""
BUILD_CHANNEL = "local"
IS_DEV_BUILD = False

try:
    from meshchatx.src._build_meta_baked import (  # type: ignore[import-not-found]
        BUILD_CHANNEL as _BAKED_CHANNEL,
        GIT_COMMIT as _BAKED_COMMIT,
        GIT_COMMIT_SHORT as _BAKED_SHORT,
        IS_DEV_BUILD as _BAKED_IS_DEV,
    )

    GIT_COMMIT = str(_BAKED_COMMIT or "")
    GIT_COMMIT_SHORT = str(_BAKED_SHORT or "")
    BUILD_CHANNEL = str(_BAKED_CHANNEL or "local")
    IS_DEV_BUILD = bool(_BAKED_IS_DEV)
except Exception:
    pass


def display_version(base_version: str) -> str:
    """Version string for UI labels (adds -dev for nightly/local builds)."""
    version = str(base_version or "").strip() or "unknown"
    if IS_DEV_BUILD and not version.endswith("-dev"):
        return f"{version}-dev"
    return version


def as_dict(base_version: str) -> dict[str, object]:
    """Fields merged into /api/v1/app/info."""
    short = (GIT_COMMIT_SHORT or "").strip()
    full = (GIT_COMMIT or "").strip()
    if not short and full:
        short = full[:7]
    return {
        "git_commit": full or short,
        "git_commit_short": short,
        "build_channel": BUILD_CHANNEL or "local",
        "is_dev_build": bool(IS_DEV_BUILD),
        "display_version": display_version(base_version),
    }
