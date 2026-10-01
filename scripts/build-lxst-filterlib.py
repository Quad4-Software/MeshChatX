#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Compile LXST's bundled filterlib for the running interpreter ABI.

Upstream LXST ships prebuilt filterlib blobs per CPython ABI
(filterlib.cpython-311-*.so ... cpython-314-*). On interpreters upstream
has not built for - currently any pre-release such as 3.15 - find_spec
cannot resolve LXST.filterlib and check_lxst_telephony fails even though
LXST itself falls back to compiling Filters.c via cffi at import.

The blob is a plain C shared object loaded through cffi dlopen, so it
needs no Python headers. This script builds it in place:

    uv run python scripts/build-lxst-filterlib.py

Exit 0 when an artifact exists or was built, 1 on a real build failure.
When no C compiler is available the script exits 2 so callers can decide
whether that is fatal (the LXST cffi fallback covers runtime use).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


def _lxst_root() -> Path | None:
    spec = importlib.util.find_spec("LXST")
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def _artifact_name() -> str:
    if sys.platform == "win32":
        return "filterlib.dll"
    ext = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    return f"filterlib{ext}"


def _pick_compiler() -> list[str] | None:
    cc = (
        os.environ.get("CC")
        or shutil.which("cc")
        or shutil.which("gcc")
        or shutil.which("clang")
    )
    return [cc] if cc else None


def main() -> int:
    root = _lxst_root()
    if root is None:
        print("build-lxst-filterlib: LXST not installed", file=sys.stderr)
        return 1

    artifact = root / _artifact_name()
    if artifact.is_file():
        print(f"build-lxst-filterlib: present {artifact.name}")
        return 0

    src = root / "Filters.c"
    if not src.is_file():
        print(f"build-lxst-filterlib: missing source {src}", file=sys.stderr)
        return 1

    cc = _pick_compiler()
    if cc is None:
        print("build-lxst-filterlib: no C compiler (cc/gcc/clang)", file=sys.stderr)
        return 2

    tmp = artifact.with_suffix(artifact.suffix + ".tmp")
    cmd = [*cc, "-O2", "-fPIC", "-shared", str(src), "-o", str(tmp), "-lm"]
    try:
        subprocess.run(cmd, check=True)
        os.replace(tmp, artifact)
    except subprocess.CalledProcessError as e:
        tmp.unlink(missing_ok=True)
        print(f"build-lxst-filterlib: compile failed: {e}", file=sys.stderr)
        return 1

    print(f"build-lxst-filterlib: built {artifact.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
