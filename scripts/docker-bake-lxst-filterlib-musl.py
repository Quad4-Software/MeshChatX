#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Alpine/musl Docker: copy cffi-built filter shared library to LXST.filterlib name.

LXST ships glibc-tagged ``filterlib*.so`` wheels; musl ignores them and cffi
``verify()`` drops the musl artifact under ``LXST/__pycache__/_cffi__*.so``.
Without this step, a fresh process cannot resolve ``LXST.filterlib`` for
``ffi.dlopen()`` and would try to compile again at runtime (no gcc).

The cffi artifact is a plain shared library (loaded via dlopen), not a Python
extension module (no ``PyInit_filterlib``); do not ``import LXST.filterlib``.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


def main() -> int:
    import LXST

    pkg = Path(LXST.__file__).resolve().parent
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ""
    target = pkg / f"filterlib{ext_suffix}"

    import LXST.Filters  # noqa: F401 — triggers cffi verify when needed

    candidates = sorted(
        pkg.glob("__pycache__/_cffi__*.cpython-*-linux-musl.so"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        print(
            "docker-bake-lxst-filterlib-musl: no musl _cffi shared library under "
            "site-packages/LXST/__pycache__ (did Filters import compile?)",
            file=sys.stderr,
        )
        return 1

    src = candidates[0]
    shutil.copy2(src, target)

    spec = importlib.util.find_spec("LXST.filterlib")
    if not spec or not spec.origin:
        print(
            "docker-bake-lxst-filterlib-musl: LXST.filterlib still not discoverable "
            f"after copying {src.name}",
            file=sys.stderr,
        )
        return 1

    verify = subprocess.run(
        [
            sys.executable,
            "-c",
            "import LXST.Filters as F; raise SystemExit(0 if F.USE_NATIVE_FILTERS else 1)",
        ],
        check=False,
    )
    if verify.returncode != 0:
        print(
            "docker-bake-lxst-filterlib-musl: fresh interpreter did not load native filters",
            file=sys.stderr,
        )
        return 1

    print(f"docker-bake-lxst-filterlib-musl: OK ({src.name} -> {target.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
