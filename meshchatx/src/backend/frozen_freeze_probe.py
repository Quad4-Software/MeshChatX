# SPDX-License-Identifier: 0BSD

"""Import probes for cx_Freeze desktop builds.

Invoked from CI and build-backend via:

  ReticulumMeshChatX --meshchatx-run-module meshchatx.src.backend.frozen_freeze_probe
"""

from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path


def _lxst_filterlib_path() -> Path | None:
    spec = importlib.util.find_spec("LXST")
    if spec is None or not spec.submodule_search_locations:
        return None
    root = Path(next(iter(spec.submodule_search_locations)))
    if not root.is_dir():
        return None
    ext = sysconfig.get_config_var("EXT_SUFFIX") or ""
    candidates: list[Path] = []
    if sys.platform == "win32":
        candidates.append(root / "filterlib.dll")
    if ext:
        candidates.append(root / f"filterlib{ext}")
    for path in candidates:
        if path.is_file():
            return path
    return None


def main() -> None:
    import email.header  # noqa: F401
    import email.message  # noqa: F401
    import email.policy  # noqa: F401

    import aiohttp  # noqa: F401

    native = _lxst_filterlib_path()
    if native is None:
        raise SystemExit("frozen-freeze-probe: LXST filterlib native artifact missing")

    print("frozen-freeze-probe ok", flush=True)


if __name__ == "__main__":
    main()
