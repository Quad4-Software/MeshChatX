#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Print a brand.json field. Usage: python3 scripts/brand.py <key> [default]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

brand = json.loads((Path(__file__).resolve().parents[1] / "brand.json").read_text())
key = sys.argv[1]
default = sys.argv[2] if len(sys.argv) > 2 else ""
value = brand.get(key, default)
if not value and key == "flatpak_repo_base_url":
    repo = brand.get("repository", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        value = f"https://{owner.lower()}.github.io/{name}/flatpak"
print(value)
