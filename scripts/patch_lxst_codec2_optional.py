#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Make LXST Codec2 import optional so missing libcodec2 does not break telephony.

Upstream LXST 0.5.x imports Codec2 unconditionally in Codecs/__init__.py.
When pycodec2/libcodec2 is missing, that raises and prevents Opus profiles
and the whole Telephone stack from loading. Android wheels already soft-import
Codec2. This patch applies the same guard to a site-packages install.

Idempotent. Safe to run after every uv sync / pip install.
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

_CODECS_MARKER = "# meshchatx-lxst-codec2-optional (do not remove)\n"

_CODECS_INIT = """# Copyright 2024-2026, Mark Qvist
# meshchatx-lxst-codec2-optional (do not remove)

from .Codec import CodecError as CodecError
from .Codec import Codec as Codec
from .Codec import Null as Null
from .Raw import Raw as Raw
from .Opus import Opus as Opus

_CODEC2_IMPORT_ERROR = None
try:
    from .Codec2 import Codec2 as Codec2
except Exception as _codec2_exc:
    Codec2 = None
    _CODEC2_IMPORT_ERROR = _codec2_exc

NULL   = 0xFF
RAW    = 0x00
OPUS   = 0x01
CODEC2 = 0x02

def _raise_codec2_unavailable():
    if _CODEC2_IMPORT_ERROR is not None:
        raise CodecError(f"Codec2 backend unavailable: {_CODEC2_IMPORT_ERROR}")
    raise CodecError("Codec2 backend unavailable")

def codec_header_byte(codec):
    if codec == Raw:
        return RAW.to_bytes()
    elif codec == Opus:
        return OPUS.to_bytes()
    elif Codec2 is not None and codec == Codec2:
        return CODEC2.to_bytes()

    raise TypeError(f"No header mapping for codec type {codec}")

def codec_type(header_byte):
    if header_byte == RAW:
        return Raw
    elif header_byte == OPUS:
        return Opus
    elif header_byte == CODEC2:
        if Codec2 is None:
            _raise_codec2_unavailable()
        return Codec2
"""

_OLD_GET_CODEC = """    @staticmethod
    def get_codec(profile):
        if   profile == Profiles.BANDWIDTH_ULTRA_LOW: return Codec2(mode=Codec2.CODEC2_700C)
        elif profile == Profiles.BANDWIDTH_VERY_LOW:  return Codec2(mode=Codec2.CODEC2_1600)
        elif profile == Profiles.BANDWIDTH_LOW:       return Codec2(mode=Codec2.CODEC2_3200)
        elif profile == Profiles.QUALITY_MEDIUM:      return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
        elif profile == Profiles.QUALITY_HIGH:        return Opus(profile=Opus.PROFILE_VOICE_HIGH)
        elif profile == Profiles.QUALITY_MAX:         return Opus(profile=Opus.PROFILE_VOICE_MAX)
        elif profile == Profiles.LATENCY_LOW:         return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
        elif profile == Profiles.LATENCY_ULTRA_LOW:   return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
        else:                                         return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
"""

_NEW_GET_CODEC = """    @staticmethod
    def get_codec(profile):
        if Codec2 is not None:
            if   profile == Profiles.BANDWIDTH_ULTRA_LOW: return Codec2(mode=Codec2.CODEC2_700C)
            elif profile == Profiles.BANDWIDTH_VERY_LOW:  return Codec2(mode=Codec2.CODEC2_1600)
            elif profile == Profiles.BANDWIDTH_LOW:       return Codec2(mode=Codec2.CODEC2_3200)
        if   profile == Profiles.QUALITY_MEDIUM:      return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
        elif profile == Profiles.QUALITY_HIGH:        return Opus(profile=Opus.PROFILE_VOICE_HIGH)
        elif profile == Profiles.QUALITY_MAX:         return Opus(profile=Opus.PROFILE_VOICE_MAX)
        elif profile == Profiles.LATENCY_LOW:         return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
        elif profile == Profiles.LATENCY_ULTRA_LOW:   return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
        else:                                         return Opus(profile=Opus.PROFILE_VOICE_MEDIUM)
"""


def _lxst_file(*parts: str) -> Path | None:
    try:
        dist = importlib.metadata.distribution("lxst")
    except importlib.metadata.PackageNotFoundError:
        return None
    for rel in dist.files or ():
        if tuple(rel.parts[-len(parts) :]) == parts:
            return Path(dist.locate_file(rel))
    return None


def main() -> int:
    codecs_init = _lxst_file("Codecs", "__init__.py")
    telephony = _lxst_file("Primitives", "Telephony.py")
    if codecs_init is None:
        print(
            "patch_lxst_codec2_optional: lxst not installed, nothing to do",
            file=sys.stderr,
        )
        return 0

    codecs_text = codecs_init.read_text(encoding="utf-8")
    if _CODECS_MARKER not in codecs_text:
        codecs_init.write_text(_CODECS_INIT, encoding="utf-8")
        print(f"patch_lxst_codec2_optional: patched Codecs/__init__.py ({codecs_init})")
    else:
        print(f"patch_lxst_codec2_optional: Codecs already patched ({codecs_init})")

    if telephony is None:
        print(
            "patch_lxst_codec2_optional: Telephony.py not found",
            file=sys.stderr,
        )
        return 1

    tel_text = telephony.read_text(encoding="utf-8")
    if "if Codec2 is not None:" in tel_text and "BANDWIDTH_ULTRA_LOW" in tel_text:
        print(
            f"patch_lxst_codec2_optional: Telephony get_codec already guarded ({telephony})",
        )
        return 0

    if _OLD_GET_CODEC not in tel_text:
        print(
            "patch_lxst_codec2_optional: unexpected Telephony get_codec layout; "
            f"manual check required ({telephony})",
            file=sys.stderr,
        )
        return 1

    telephony.write_text(
        tel_text.replace(_OLD_GET_CODEC, _NEW_GET_CODEC, 1),
        encoding="utf-8",
    )
    print(f"patch_lxst_codec2_optional: patched Telephony get_codec ({telephony})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
