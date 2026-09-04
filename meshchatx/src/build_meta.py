# SPDX-License-Identifier: 0BSD
"""Baked build metadata (git commit and channel).

Defaults keep source checkouts and tests working without a bake step.
Builds run scripts/bake_build_meta.js which writes _build_meta_baked.py
(gitignored). Packaging includes that overlay when present.
"""

from __future__ import annotations

import json
from typing import Any

GIT_COMMIT = ""
GIT_COMMIT_SHORT = ""
BUILD_CHANNEL = "local"
IS_DEV_BUILD = False
CHANNEL_PROMPT_JSON = ""

_DEFAULT_PROMPT: dict[str, Any] = {
    "bug_report_lxmf": "f489752fbef161c64d65e385a4e9fc74",
    "bug_report_url": "",
    "bug_report_steps": [
        "Send an LXMF message to f489752fbef161c64d65e385a4e9fc74",
        "Include version, channel, and git commit from About",
        "Describe steps to reproduce and expected vs actual",
        "Attach logs and screenshots if needed",
        "Note platform: Electron, Android, or self-host",
    ],
    "focus_areas": [],
    "notes": "",
}

try:
    from meshchatx.src._build_meta_baked import (  # type: ignore[import-not-found]
        BUILD_CHANNEL as _BAKED_CHANNEL,
    )
    from meshchatx.src._build_meta_baked import (
        CHANNEL_PROMPT_JSON as _BAKED_PROMPT_JSON,
    )
    from meshchatx.src._build_meta_baked import (
        GIT_COMMIT as _BAKED_COMMIT,
    )
    from meshchatx.src._build_meta_baked import (
        GIT_COMMIT_SHORT as _BAKED_SHORT,
    )
    from meshchatx.src._build_meta_baked import (
        IS_DEV_BUILD as _BAKED_IS_DEV,
    )

    GIT_COMMIT = str(_BAKED_COMMIT or "")
    GIT_COMMIT_SHORT = str(_BAKED_SHORT or "")
    BUILD_CHANNEL = str(_BAKED_CHANNEL or "local")
    IS_DEV_BUILD = bool(_BAKED_IS_DEV)
    CHANNEL_PROMPT_JSON = str(_BAKED_PROMPT_JSON or "")
except Exception:
    pass


def normalize_channel(raw: str | None) -> str:
    """Map legacy bake names to product channels."""
    c = str(raw or "").strip().lower()
    if not c:
        return "local"
    if c in ("nightly", "testing"):
        return "testing"
    if c in ("preview", "preview-dev", "beta"):
        return "beta"
    if c in ("release", "stable"):
        return "stable"
    if c == "local":
        return "local"
    return c


def channel_prompt_dict() -> dict[str, Any]:
    """Parsed channel prompt for Testing/Beta UI."""
    raw = (CHANNEL_PROMPT_JSON or "").strip()
    if not raw:
        return dict(_DEFAULT_PROMPT)
    try:
        parsed = json.loads(raw)
    except Exception:
        return dict(_DEFAULT_PROMPT)
    if not isinstance(parsed, dict):
        return dict(_DEFAULT_PROMPT)
    steps = parsed.get("bug_report_steps")
    areas = parsed.get("focus_areas")
    url = parsed.get("bug_report_url")
    lxmf = parsed.get("bug_report_lxmf")
    notes = parsed.get("notes")
    return {
        "bug_report_lxmf": (
            str(lxmf).strip().lower()
            if isinstance(lxmf, str) and lxmf.strip()
            else str(_DEFAULT_PROMPT["bug_report_lxmf"])
        ),
        "bug_report_url": str(url).strip() if isinstance(url, str) else "",
        "bug_report_steps": (
            [str(s) for s in steps if str(s).strip()]
            if isinstance(steps, list)
            else list(_DEFAULT_PROMPT["bug_report_steps"])
        ),
        "focus_areas": (
            [str(s) for s in areas if str(s).strip()] if isinstance(areas, list) else []
        ),
        "notes": str(notes) if isinstance(notes, str) else "",
    }


def display_version(base_version: str) -> str:
    """Version string for UI labels (adds -dev for non-stable builds)."""
    version = str(base_version or "").strip() or "unknown"
    channel = normalize_channel(BUILD_CHANNEL)
    if channel != "stable" and not version.endswith("-dev"):
        return f"{version}-dev"
    return version


def as_dict(base_version: str) -> dict[str, object]:
    """Fields merged into /api/v1/app/info."""
    short = (GIT_COMMIT_SHORT or "").strip()
    full = (GIT_COMMIT or "").strip()
    if not short and full:
        short = full[:7]
    channel = normalize_channel(BUILD_CHANNEL)
    is_dev = channel != "stable"
    return {
        "git_commit": full or short,
        "git_commit_short": short,
        "build_channel": channel,
        "is_dev_build": is_dev,
        "display_version": display_version(base_version),
        "channel_prompt": channel_prompt_dict(),
    }
