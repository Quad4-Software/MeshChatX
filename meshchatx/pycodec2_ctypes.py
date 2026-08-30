# SPDX-License-Identifier: 0BSD

"""ctypes-backed pycodec2-compatible Codec2 for Android when the extension is broken.

Chaquopy vendor wheels have shipped an empty pycodec2.so (no PyInit). libcodec2.so
is valid and preloaded. This module exposes the subset of the pycodec2 API that
LXST.Codecs.Codec2 and MeshChatX probes need.
"""

from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# codec2.h mode constants (bitrate arg maps through this table)
_MODES = {
    700: 8,  # CODEC2_MODE_700C
    1200: 5,
    1300: 4,
    1400: 3,
    1600: 2,
    2400: 1,
    3200: 0,
}

_lib: ctypes.CDLL | None = None
_lib_error: str | None = None


class _CODEC2(ctypes.Structure):
    pass


_CODEC2_p = ctypes.POINTER(_CODEC2)


def _cdll_load(path_or_name: str) -> ctypes.CDLL:
    mode = getattr(ctypes, "RTLD_GLOBAL", None)
    if mode is None:
        return ctypes.CDLL(path_or_name)
    return ctypes.CDLL(path_or_name, mode=mode)


def _candidate_lib_paths() -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        if value and value not in seen:
            seen.add(value)
            paths.append(value)

    explicit = os.environ.get("MESHCHAT_LIBCODEC2_PATH", "") or ""
    if explicit:
        add(explicit)
    native_dir = os.environ.get("MESHCHAT_NATIVE_LIB_DIR", "") or ""
    if native_dir:
        add(str(Path(native_dir) / "libcodec2.so"))
    for entry in list(__import__("sys").path):
        if not entry:
            continue
        root = Path(entry)
        add(str(root / "pycodec2" / "libcodec2.so"))
        add(str(root / "chaquopy" / "lib" / "libcodec2.so"))
        add(str(root / "libcodec2.so"))
    add("libcodec2.so")
    return paths


def _bind(lib: ctypes.CDLL) -> None:
    lib.codec2_create.argtypes = [ctypes.c_int]
    lib.codec2_create.restype = _CODEC2_p
    lib.codec2_destroy.argtypes = [_CODEC2_p]
    lib.codec2_destroy.restype = None
    lib.codec2_encode.argtypes = [
        _CODEC2_p,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_short),
    ]
    lib.codec2_encode.restype = None
    lib.codec2_decode.argtypes = [
        _CODEC2_p,
        ctypes.POINTER(ctypes.c_short),
        ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.codec2_decode.restype = None
    lib.codec2_samples_per_frame.argtypes = [_CODEC2_p]
    lib.codec2_samples_per_frame.restype = ctypes.c_int
    lib.codec2_bits_per_frame.argtypes = [_CODEC2_p]
    lib.codec2_bits_per_frame.restype = ctypes.c_int
    lib.codec2_bytes_per_frame.argtypes = [_CODEC2_p]
    lib.codec2_bytes_per_frame.restype = ctypes.c_int


def load_libcodec2(*, force: bool = False) -> ctypes.CDLL:
    """Load and bind libcodec2 for ctypes Codec2 wrappers."""
    global _lib, _lib_error
    if _lib is not None and not force:
        return _lib
    last_error: str | None = None
    for candidate in _candidate_lib_paths():
        try:
            if candidate != "libcodec2.so" and not Path(candidate).is_file():
                continue
            lib = _cdll_load(candidate)
            _bind(lib)
            # Touch create/destroy so we fail early on a stub library.
            state = lib.codec2_create(_MODES[1600])
            if not state:
                raise OSError("codec2_create returned NULL")
            lib.codec2_destroy(state)
            _lib = lib
            _lib_error = None
            logger.info("pycodec2_ctypes loaded libcodec2 from %s", candidate)
            return lib
        except Exception as exc:
            last_error = f"{candidate}: {exc}"
    _lib = None
    _lib_error = last_error or "libcodec2.so not found"
    raise OSError(_lib_error)


def libcodec2_load_error() -> str | None:
    return _lib_error


class Codec2:
    """Minimal pycodec2.Codec2 stand-in used by LXST."""

    def __init__(self, mode: int):
        if mode not in _MODES:
            raise ValueError(f"Unsupported Codec2 mode: {mode}")
        lib = load_libcodec2()
        self._lib = lib
        self._state = lib.codec2_create(_MODES[mode])
        if not self._state:
            raise MemoryError("codec2_create failed")

    def __del__(self):
        state = getattr(self, "_state", None)
        lib = getattr(self, "_lib", None)
        if state and lib is not None:
            try:
                lib.codec2_destroy(state)
            except Exception:
                pass
            self._state = None

    def samples_per_frame(self) -> int:
        return int(self._lib.codec2_samples_per_frame(self._state))

    def bits_per_frame(self) -> int:
        return int(self._lib.codec2_bits_per_frame(self._state))

    def bytes_per_frame(self) -> int:
        return int(self._lib.codec2_bytes_per_frame(self._state))

    def encode(self, speech_in):
        import numpy as np

        samples = np.ascontiguousarray(speech_in, dtype=np.int16)
        spf = self.samples_per_frame()
        if samples.size == 0 or samples.size % spf != 0:
            raise AssertionError(
                "encode input length must be a multiple of samples_per_frame",
            )
        frames = samples.size // spf
        bpf = self.bytes_per_frame()
        out = (ctypes.c_uint8 * (frames * bpf))()
        for index in range(frames):
            frame_speech = (ctypes.c_short * spf).from_buffer(samples, index * spf * 2)
            frame_bits = ctypes.cast(
                ctypes.addressof(out) + index * bpf,
                ctypes.POINTER(ctypes.c_uint8),
            )
            self._lib.codec2_encode(self._state, frame_bits, frame_speech)
        return bytes(out)

    def decode(self, frames: bytes):
        import numpy as np

        raw = bytes(frames)
        bpf = self.bytes_per_frame()
        if len(raw) < bpf:
            raise AssertionError("decode input shorter than bytes_per_frame")
        frame_count = len(raw) // bpf
        spf = self.samples_per_frame()
        speech = np.empty(frame_count * spf, dtype=np.int16)
        for index in range(frame_count):
            chunk = raw[index * bpf : (index + 1) * bpf]
            bit_buf = (ctypes.c_uint8 * bpf).from_buffer_copy(chunk)
            frame_speech = (ctypes.c_short * spf).from_buffer(speech, index * spf * 2)
            self._lib.codec2_decode(
                self._state,
                frame_speech,
                ctypes.cast(bit_buf, ctypes.POINTER(ctypes.c_uint8)),
            )
        return speech


def probe() -> tuple[bool, str | None]:
    """Return whether ctypes Codec2 can construct and report frame sizes."""
    try:
        c2 = Codec2(1600)
        _ = c2.samples_per_frame()
        _ = c2.bytes_per_frame()
        return True, None
    except Exception as exc:
        return False, str(exc)
