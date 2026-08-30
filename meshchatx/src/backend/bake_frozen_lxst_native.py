# SPDX-License-Identifier: 0BSD

"""Prune alien LXST filterlib blobs after cx_Freeze."""

from __future__ import annotations

import sys
import sysconfig
from pathlib import Path


def _should_keep_filterlib(name: str, ext_suffix: str) -> bool:
    if sys.platform == "win32" and name == "filterlib.dll":
        return True
    if ext_suffix and name == f"filterlib{ext_suffix}":
        return True
    return False


def bake_lxst_filterlib(build_dir: Path) -> None:
    lxst = build_dir / "lib" / "LXST"
    if not lxst.is_dir():
        raise SystemExit(f"bake_frozen_lxst_native: missing {lxst}")

    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ""
    removed = 0
    kept: list[str] = []
    for path in sorted(lxst.glob("filterlib*")):
        if not path.is_file():
            continue
        if _should_keep_filterlib(path.name, ext_suffix):
            kept.append(path.name)
            continue
        path.unlink()
        removed += 1

    if not kept:
        raise SystemExit(
            "bake_frozen_lxst_native: no filterlib native artifact for this platform "
            f"({sys.platform}, EXT_SUFFIX={ext_suffix!r})",
        )

    print(
        f"bake_frozen_lxst_native: OK kept {kept!r} (removed {removed} alien blob(s))",
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: python -m meshchatx.src.backend.bake_frozen_lxst_native <build dir>",
        )
    bake_lxst_filterlib(Path(sys.argv[1]).resolve())


if __name__ == "__main__":
    main()
