# SPDX-License-Identifier: 0BSD

"""Load Codec2 native libraries before pycodec2/LXST on Chaquopy Android."""

from __future__ import annotations

import ctypes
import logging
import os
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


def _cdll_load(path_or_name: str):
    """Load a shared library with RTLD_GLOBAL when the platform supports it.

    pycodec2.so declares NEEDED libcodec2.so. Loading with RTLD_GLOBAL lets the
    later dlopen of the extension resolve that dependency.
    """
    mode = getattr(ctypes, "RTLD_GLOBAL", None)
    if mode is None:
        return ctypes.CDLL(path_or_name)
    return ctypes.CDLL(path_or_name, mode=mode)


def _libcodec2_candidates() -> list[Path]:
    """Return candidate paths for libcodec2.so without importing pycodec2.

    import pycodec2 loads the extension which already needs libcodec2.so.
    Searching sys.path on disk avoids that chicken-and-egg failure.
    """
    candidates: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        candidates.append(path)

    explicit = Path(os.environ.get("MESHCHAT_LIBCODEC2_PATH", "") or "")
    if explicit.is_file():
        add(explicit)

    for entry in sys.path:
        if not entry:
            continue
        root = Path(entry)
        add(root / "pycodec2" / "libcodec2.so")
        add(root / "chaquopy" / "lib" / "libcodec2.so")
        # Some Chaquopy layouts nest native libs under site-packages directly.
        add(root / "libcodec2.so")

    # Extracted APK native lib dirs (ABI-specific jniLibs sync target).
    for env_key in ("MESHCHAT_NATIVE_LIB_DIR", "ANDROID_NATIVE_LIBRARY_DIR"):
        native_dir = Path(os.environ.get(env_key, "") or "")
        if native_dir.is_dir():
            add(native_dir / "libcodec2.so")

    return candidates


def _java_system_load_library(name: str = "codec2") -> bool:
    """Ask the Android runtime to load a jniLibs shared object by soname."""
    try:
        from java.lang import System as JavaSystem

        JavaSystem.loadLibrary(name)
        return True
    except Exception as exc:
        logger.debug("Java System.loadLibrary(%s) failed: %s", name, exc)
        return False


def ensure_codec2_native_library() -> bool:
    """Preload libcodec2.so so import pycodec2 works on Android.

    Chaquopy installs chaquopy-libcodec2 separately from pycodec2. The
    extension module only declares a NEEDED entry for libcodec2.so. Without
    preloading or bundling the shared library next to pycodec2.so, imports
    fail at runtime with dlopen errors.

    Order: Java System.loadLibrary (jniLibs), bare CDLL name, then absolute
    candidate paths including MESHCHAT_NATIVE_LIB_DIR.
    """
    global _codec2_preload_done, _codec2_preload_error

    if _codec2_preload_done:
        return _codec2_preload_error is None

    _codec2_preload_done = True

    if not _is_chaquopy_android():
        return True

    if _java_system_load_library("codec2"):
        logger.info("Loaded Codec2 via Java System.loadLibrary(codec2)")
        return True

    try:
        _cdll_load("libcodec2.so")
        return True
    except OSError:
        pass

    last_error: str | None = None
    for lib_path in _libcodec2_candidates():
        if not lib_path.is_file():
            continue
        try:
            _cdll_load(str(lib_path))
            logger.info("Loaded Codec2 native library from %s", lib_path)
            return True
        except OSError as exc:
            last_error = f"{lib_path}: {exc}"

    _codec2_preload_error = last_error or "libcodec2.so not found on Android"
    logger.warning("Codec2 native preload failed: %s", _codec2_preload_error)
    return False


def probe_pycodec2() -> tuple[bool, str | None]:
    """Import pycodec2 after preload and report whether Codec2 works."""
    if _is_chaquopy_android() and not ensure_codec2_native_library():
        return False, codec2_preload_error()
    try:
        import pycodec2

        c2 = pycodec2.Codec2(1600)
        _ = c2.samples_per_frame()
        return True, None
    except Exception as exc:
        return False, str(exc)


def codec2_preload_error() -> str | None:
    """Return the last preload failure message, if any."""
    return _codec2_preload_error


def reset_codec2_preload_state_for_tests() -> None:
    """Clear preload memoization (tests only)."""
    global _codec2_preload_done, _codec2_preload_error
    _codec2_preload_done = False
    _codec2_preload_error = None
