# SPDX-License-Identifier: 0BSD
"""Ensure LXST vendored pyogg exports ctypes aliases Opus needs.

Upstream ogg.py defines c_int_p and related names only inside
if PYOGG_OGG_AVAIL. When libopus loads but libogg does not, opus.py
still references those names and raises NameError on import.

Docker and Taskfile run a post-install disk patch. Plain pip install
does not, so MeshChatX applies the same fix before importing LXST.
"""

from __future__ import annotations

import importlib.abc
import importlib.metadata
import importlib.util
import sys
from ctypes import POINTER, c_char_p, c_float, c_int, c_ubyte
from pathlib import Path

_MARKER = "# meshchatx-lxst-pyogg-ctypes-compat (do not remove; idempotency)\n"

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

_OGG_MODULE = "LXST.Codecs.libs.pyogg.ogg"
_HOOK_INSTALLED = False

_ALIAS_VALUES = {
    "c_int_p": POINTER(c_int),
    "c_float_p": POINTER(c_float),
    "c_uchar_p": POINTER(c_ubyte),
    "c_char_p_p": POINTER(c_char_p),
    "c_uchar": c_ubyte,
}


def find_ogg_py() -> Path | None:
    """Locate LXST bundled pyogg ogg.py without importing LXST."""
    try:
        dist = importlib.metadata.distribution("lxst")
    except importlib.metadata.PackageNotFoundError:
        return None
    for rel in dist.files or ():
        parts = rel.parts
        if len(parts) >= 2 and parts[-2] == "pyogg" and parts[-1] == "ogg.py":
            return Path(str(dist.locate_file(rel)))
    return None


def inject_ctypes_aliases(ogg_module) -> list[str]:
    """Set missing ctypes aliases on a loaded ogg module. Returns names set."""
    added: list[str] = []
    for name, value in _ALIAS_VALUES.items():
        if not hasattr(ogg_module, name):
            setattr(ogg_module, name, value)
            added.append(name)
    return added


def apply_disk_patch(ogg: Path | None = None) -> str:
    """Patch ogg.py on disk. Returns status token."""
    target = ogg if ogg is not None else find_ogg_py()
    if target is None:
        return "missing"
    text = target.read_text(encoding="utf-8")
    if _MARKER in text:
        return "already"
    if _LEGACY_BLOCK in text:
        target.write_text(text.replace(_LEGACY_BLOCK, _INSERT, 1), encoding="utf-8")
        return "upgraded"
    if _NEEDLE not in text:
        return "unexpected"
    target.write_text(text.replace(_NEEDLE, _NEEDLE + _INSERT, 1), encoding="utf-8")
    return "patched"


class _OggCompatLoader(importlib.abc.Loader):
    """Load ogg.py then inject module-level ctypes aliases."""

    def __init__(self, origin: Path):
        self.origin = origin

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = self.origin.read_text(encoding="utf-8")
        code = compile(source, str(self.origin), "exec")
        exec(code, module.__dict__)
        inject_ctypes_aliases(module)


class _OggCompatFinder(importlib.abc.MetaPathFinder):
    """Intercept LXST pyogg ogg import when disk patch is unavailable."""

    def find_spec(self, fullname, path, target=None):
        if fullname != _OGG_MODULE:
            return None
        if fullname in sys.modules:
            return None
        ogg = find_ogg_py()
        if ogg is None or not ogg.is_file():
            return None
        try:
            text = ogg.read_text(encoding="utf-8")
        except OSError:
            return None
        if _MARKER in text:
            return None
        loader = _OggCompatLoader(ogg)
        return importlib.util.spec_from_file_location(
            fullname,
            ogg,
            loader=loader,
            submodule_search_locations=None,
        )


def install_import_hook() -> bool:
    """Install a one-shot meta path finder for read-only site-packages."""
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return False
    for finder in sys.meta_path:
        if isinstance(finder, _OggCompatFinder):
            _HOOK_INSTALLED = True
            return False
    sys.meta_path.insert(0, _OggCompatFinder())
    _HOOK_INSTALLED = True
    return True


def ensure_lxst_pyogg_ctypes_compat() -> str:
    """Disk-patch when possible and install an import hook as fallback.

    Safe to call repeatedly. Does not import LXST.
    """
    status = "skipped"
    try:
        status = apply_disk_patch()
    except OSError:
        status = "readonly"
    install_import_hook()
    existing = sys.modules.get(_OGG_MODULE)
    if existing is not None:
        inject_ctypes_aliases(existing)
    return status


def patch_cli() -> int:
    """CLI used by scripts/patch_lxst_pyogg_ogg_ctypes.py."""
    try:
        status = apply_disk_patch()
    except OSError as exc:
        print(f"patch_lxst_pyogg_ogg_ctypes: write failed ({exc})", file=sys.stderr)
        return 1
    ogg = find_ogg_py()
    if status == "missing":
        print(
            "patch_lxst_pyogg_ogg_ctypes: lxst not installed, nothing to do",
            file=sys.stderr,
        )
        return 0
    if status == "already":
        print(f"patch_lxst_pyogg_ogg_ctypes: already applied ({ogg})")
        return 0
    if status == "upgraded":
        print(f"patch_lxst_pyogg_ogg_ctypes: upgraded legacy block ({ogg})")
        return 0
    if status == "unexpected":
        print(
            "patch_lxst_pyogg_ogg_ctypes: unexpected ogg.py layout; "
            f"manual check required ({ogg})",
            file=sys.stderr,
        )
        return 1
    print(f"patch_lxst_pyogg_ogg_ctypes: patched {ogg}")
    return 0
