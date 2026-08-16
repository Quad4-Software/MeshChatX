# SPDX-License-Identifier: 0BSD

"""mutmut mutants/ must include meshchatx modules outside src/backend."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mutmut_config() -> dict:
    data = tomllib.loads((_root() / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["mutmut"]


def _also_copy_covers(rel: Path, also_copy: list[str]) -> bool:
    rel_s = rel.as_posix()
    for item in also_copy:
        normalized = item.rstrip("/")
        if rel_s == item or rel_s == normalized:
            return True
        if rel_s.startswith(normalized + "/"):
            return True
    return False


def test_mutmut_also_copy_covers_package_modules_outside_backend():
    also_copy = list(_mutmut_config().get("also_copy", []))
    root = _root()
    required = sorted(
        path
        for path in (
            list((root / "meshchatx").glob("*.py"))
            + list((root / "meshchatx" / "src").glob("*.py"))
        )
        if path.name != "_build_meta_baked.py"
    )
    missing = [
        path.relative_to(root).as_posix()
        for path in required
        if not _also_copy_covers(path.relative_to(root), also_copy)
    ]
    assert missing == []
