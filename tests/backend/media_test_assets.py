# SPDX-License-Identifier: 0BSD

"""Shared bytes for media API and golden regression tests (PNG, GIF, gzip TGS)."""

from __future__ import annotations

import gzip
import json

TINY_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * 32

TINY_GIF = b"GIF89a" + b"\x00" * 32

_LOTTIE_MIN = {
    "v": "5.0.0",
    "fr": 30.0,
    "ip": 0.0,
    "op": 60.0,
    "w": 512,
    "h": 512,
    "nm": "golden",
    "ddd": 0,
    "assets": [],
    "layers": [],
}

GZIP_TGS_512: bytes = gzip.compress(json.dumps(_LOTTIE_MIN).encode("ascii"))
