# SPDX-License-Identifier: 0BSD

"""Reticulum MeshChatX - A mesh network communications app."""

import re
from pathlib import Path

_vpath = Path(__file__).resolve().parent / "src" / "version.py"
_m = re.search(
    r'^__version__\s*=\s*["\']([^"\']+)["\']',
    _vpath.read_text(encoding="utf-8"),
    re.MULTILINE,
)
if not _m:
    raise RuntimeError("meshchatx/src/version.py: missing __version__ line")
__version__ = _m.group(1)
