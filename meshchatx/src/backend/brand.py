# SPDX-License-Identifier: 0BSD
"""Project brand constants loaded from the repo-root brand.json.

Every value is a non-empty string. fields marked optional in brand.json may
be empty and are then derived from ``repository``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_DEFAULTS = {
    "name": "MeshChatX",
    "product_name": "Reticulum MeshChatX",
    "slug": "meshchatx",
    "app_id": "com.meshchatx.app",
    "repository": "Quad4-Software/MeshChatX",
    "homepage": "https://meshchatx.com",
    "issues_url": "",
    "container_image": "ghcr.io/quad4-software/meshchatx",
    "docker_hub_image": "quad4io/meshchatx",
    "flatpak_repo_base_url": "",
    "copyright_holder": "MeshChatX contributors",
    "security_contact": "security@quad4.io",
}


def _derive(values: dict) -> dict:
    out = dict(values)
    repo = out.get("repository") or ""
    if not out.get("issues_url"):
        out["issues_url"] = f"https://github.com/{repo}/issues" if repo else ""
    if not out.get("flatpak_repo_base_url"):
        if "/" in repo:
            owner, name = repo.split("/", 1)
            out["flatpak_repo_base_url"] = (
                f"https://{owner.lower()}.github.io/{name}/flatpak"
            )
        else:
            out["flatpak_repo_base_url"] = ""
    return out


@lru_cache(maxsize=1)
def brand() -> dict:
    values = dict(_DEFAULTS)
    path = _REPO_ROOT / "brand.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        data = {}
    if isinstance(data, dict):
        for key in _DEFAULTS:
            if key in data:
                values[key] = data[key]
    out = _derive(values)
    for key, value in out.items():
        if not isinstance(value, str):
            raise TypeError(f"brand field {key} must be a string")
    return out


def get(key: str, default: str = "") -> str:
    return brand().get(key, default)
