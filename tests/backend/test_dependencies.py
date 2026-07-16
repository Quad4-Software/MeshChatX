# SPDX-License-Identifier: 0BSD

"""Core runtime dependency contract tests."""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path


def _project_dependencies() -> list[str]:
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return list(data["project"]["dependencies"])


def test_bleak_declared_in_pyproject():
    assert any(dep.startswith("bleak") for dep in _project_dependencies())


def test_bleak_importable():
    assert importlib.util.find_spec("bleak") is not None
