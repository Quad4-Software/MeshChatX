#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Patch LXST bundled pyogg ogg.py for missing ctypes aliases.

opus.py does from .ogg import * but needs extra ctypes names that
ogg.py only defines when libogg loads. Idempotent: safe after every
pip install / poetry install / uv sync.

MeshChatX also applies this at package import for plain PyPI installs.
This script remains for Docker, CI, and packaging (including the Docker
deps layer before the project package is installed).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_compat():
    try:
        from meshchatx.src.backend.lxst_pyogg_ctypes_compat import patch_cli

        return patch_cli
    except ImportError:
        pass
    path = (
        Path(__file__).resolve().parents[1]
        / "meshchatx"
        / "src"
        / "backend"
        / "lxst_pyogg_ctypes_compat.py"
    )
    spec = importlib.util.spec_from_file_location(
        "lxst_pyogg_ctypes_compat",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load compat module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.patch_cli


if __name__ == "__main__":
    raise SystemExit(_load_compat()())
