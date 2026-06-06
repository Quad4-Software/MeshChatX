# SPDX-License-Identifier: 0BSD

"""Load Codec2 native libraries before pycodec2/LXST on Chaquopy Android."""

from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_codec2_preload_error: str | None = None
_codec2_preload_done = False


def _is_chaquopy_android() -> bool:
    try:
        import java  # noqa: F401
    except ImportError:
        return False
    return True


def _libcodec2_candidates() -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        candidates.append(path)

    try:
        import pycodec2

        add(Path(pycodec2.__file__).resolve().parent / "libcodec2.so")
    except Exception:
        pass

    for entry in sys.path:
        if not entry:
            continue
        add(Path(entry) / "chaquopy" / "lib" / "libcodec2.so")

    return candidates


def ensure_codec2_native_library() -> bool:
    """Preload ``libcodec2.so`` so ``import pycodec2`` works on Android.

    Chaquopy installs ``chaquopy-libcodec2`` separately from ``pycodec2``. The
    extension module only declares a NEEDED entry for ``libcodec2.so``; without
    preloading or bundling the shared library next to ``pycodec2.so``, imports
    fail at runtime with ``dlopen`` errors.
    """
    global _codec2_preload_done, _codec2_preload_error

    if _codec2_preload_done:
        return _codec2_preload_error is None

    _codec2_preload_done = True

    if not _is_chaquopy_android():
        return True

    try:
        ctypes.CDLL("libcodec2.so")
        return True
    except OSError:
        pass

    last_error: str | None = None
    for lib_path in _libcodec2_candidates():
        if not lib_path.is_file():
            continue
        try:
            ctypes.CDLL(str(lib_path))
            logger.info("Loaded Codec2 native library from %s", lib_path)
            return True
        except OSError as exc:
            last_error = f"{lib_path}: {exc}"

    _codec2_preload_error = last_error or "libcodec2.so not found on Android"
    logger.warning("Codec2 native preload failed: %s", _codec2_preload_error)
    return False


def codec2_preload_error() -> str | None:
    """Return the last preload failure message, if any."""
    return _codec2_preload_error
