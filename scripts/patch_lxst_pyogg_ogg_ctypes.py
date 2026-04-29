#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Patch LXST bundled pyogg ``ogg.py`` for Python 3.14+.

``opus.py`` does ``from .ogg import *`` but needs extra ctypes names that
``ogg.py`` never defined: POINTER aliases, and ``c_uchar`` (used as ``c_uchar*0``
for flexible array argtypes; same layout as ``c_ubyte``).

Idempotent: safe to run after every ``pip install`` / ``poetry install``.
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

_MARKER = "# meshchatx-lxst-pyogg-ctypes-compat (do not remove; idempotency)\n"

# First revision (older Docker/local installs): bump handled below.
_LEGACY_MARKER = (
    "# meshchatx-lxst-pyogg-ctypes-pointer-aliases (do not remove; idempotency)\n"
)

_LEGACY_BLOCK = (
    _LEGACY_MARKER
    + "c_int_p = POINTER(c_int)\n"
    + "c_float_p = POINTER(c_float)\n"
    + "c_uchar_p = POINTER(c_ubyte)\n"
    + "c_char_p_p = POINTER(c_char_p)\n"
)

_INSERT = (
    _MARKER
    + "c_int_p = POINTER(c_int)\n"
    + "c_float_p = POINTER(c_float)\n"
    + "c_uchar_p = POINTER(c_ubyte)\n"
    + "c_char_p_p = POINTER(c_char_p)\n"
    + "c_uchar = c_ubyte\n"
)

_NEEDLE = (
    "from ctypes import c_int, c_int8, c_int16, c_int32, c_int64, c_uint, c_uint8, "
    "c_uint16, c_uint32, c_uint64, c_float, c_long, c_ulong, c_char, c_char_p, "
    "c_ubyte, c_longlong, c_ulonglong, c_size_t, c_void_p, c_double, POINTER, "
    "pointer, cast\n"
)


def _find_ogg_py() -> Path | None:
    try:
        dist = importlib.metadata.distribution("lxst")
    except importlib.metadata.PackageNotFoundError:
        return None
    for rel in dist.files or ():
        parts = rel.parts
        if len(parts) >= 2 and parts[-2] == "pyogg" and parts[-1] == "ogg.py":
            return Path(dist.locate_file(rel))
    return None


def main() -> int:
    ogg = _find_ogg_py()
    if ogg is None:
        print(
            "patch_lxst_pyogg_ogg_ctypes: lxst not installed, nothing to do",
            file=sys.stderr,
        )
        return 0
    text = ogg.read_text(encoding="utf-8")

    if _MARKER in text:
        print(f"patch_lxst_pyogg_ogg_ctypes: already applied ({ogg})")
        return 0

    if _LEGACY_BLOCK in text:
        ogg.write_text(text.replace(_LEGACY_BLOCK, _INSERT, 1), encoding="utf-8")
        print(f"patch_lxst_pyogg_ogg_ctypes: upgraded legacy block ({ogg})")
        return 0

    if _NEEDLE not in text:
        print(
            "patch_lxst_pyogg_ogg_ctypes: unexpected ogg.py layout; "
            f"manual check required ({ogg})",
            file=sys.stderr,
        )
        return 1

    ogg.write_text(text.replace(_NEEDLE, _NEEDLE + _INSERT, 1), encoding="utf-8")
    print(f"patch_lxst_pyogg_ogg_ctypes: patched {ogg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
