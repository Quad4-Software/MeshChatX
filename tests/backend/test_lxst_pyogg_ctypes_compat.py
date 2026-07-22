# SPDX-License-Identifier: 0BSD
"""Tests for LXST pyogg ctypes alias compatibility."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from meshchatx.src.backend import lxst_pyogg_ctypes_compat as compat


_NEEDLE = compat._NEEDLE


def _ogg_source(*, with_marker: bool = False, with_legacy: bool = False) -> str:
    body = _NEEDLE
    if with_marker:
        body += compat._INSERT
    elif with_legacy:
        body += compat._LEGACY_BLOCK
    body += textwrap.dedent(
        """
        libogg = None
        PYOGG_OGG_AVAIL = False
        """
    )
    return body


def test_apply_disk_patch_inserts_module_level_aliases(tmp_path: Path):
    ogg = tmp_path / "ogg.py"
    ogg.write_text(_ogg_source(), encoding="utf-8")

    assert compat.apply_disk_patch(ogg) == "patched"
    text = ogg.read_text(encoding="utf-8")
    assert compat._MARKER in text
    assert "c_int_p = POINTER(c_int)" in text
    assert "c_uchar = c_ubyte" in text
    assert compat.apply_disk_patch(ogg) == "already"


def test_apply_disk_patch_upgrades_legacy_block(tmp_path: Path):
    ogg = tmp_path / "ogg.py"
    ogg.write_text(_ogg_source(with_legacy=True), encoding="utf-8")

    assert compat.apply_disk_patch(ogg) == "upgraded"
    text = ogg.read_text(encoding="utf-8")
    assert compat._MARKER in text
    assert compat._LEGACY_MARKER not in text
    assert "c_uchar = c_ubyte" in text


def test_apply_disk_patch_unexpected_layout(tmp_path: Path):
    ogg = tmp_path / "ogg.py"
    ogg.write_text("print('not pyogg')\n", encoding="utf-8")
    assert compat.apply_disk_patch(ogg) == "unexpected"


def test_inject_ctypes_aliases_only_fills_missing():
    module = type(sys)("fake_ogg")
    module.c_int_p = object()
    added = compat.inject_ctypes_aliases(module)
    assert "c_int_p" not in added
    assert "c_float_p" in added
    assert "c_uchar" in added
    assert hasattr(module, "c_float_p")
    assert hasattr(module, "c_uchar")


def test_import_hook_loader_injects_aliases(tmp_path: Path):
    ogg = tmp_path / "ogg.py"
    ogg.write_text(_ogg_source(), encoding="utf-8")
    module = type(sys)("test_ogg_compat")
    module.__file__ = str(ogg)
    compat._OggCompatLoader(ogg).exec_module(module)
    assert hasattr(module, "c_int_p")
    assert hasattr(module, "c_uchar")
    assert module.PYOGG_OGG_AVAIL is False


def test_finder_returns_spec_only_when_unpatched(tmp_path: Path, monkeypatch):
    ogg = tmp_path / "ogg.py"
    ogg.write_text(_ogg_source(), encoding="utf-8")
    monkeypatch.setattr(compat, "find_ogg_py", lambda: ogg)
    sys.modules.pop(compat._OGG_MODULE, None)
    finder = compat._OggCompatFinder()
    spec = finder.find_spec(compat._OGG_MODULE, None)
    assert spec is not None
    assert isinstance(spec.loader, compat._OggCompatLoader)

    ogg.write_text(_ogg_source(with_marker=True), encoding="utf-8")
    assert finder.find_spec(compat._OGG_MODULE, None) is None


def test_ensure_prefers_disk_patch(tmp_path: Path, monkeypatch):
    ogg = tmp_path / "ogg.py"
    ogg.write_text(_ogg_source(), encoding="utf-8")
    monkeypatch.setattr(compat, "find_ogg_py", lambda: ogg)
    compat._HOOK_INSTALLED = False
    sys.meta_path[:] = [
        f for f in sys.meta_path if not isinstance(f, compat._OggCompatFinder)
    ]

    status = compat.ensure_lxst_pyogg_ctypes_compat()
    assert status == "patched"
    assert compat._MARKER in ogg.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        ("missing", 0),
        ("already", 0),
        ("upgraded", 0),
        ("patched", 0),
        ("unexpected", 1),
    ],
)
def test_patch_cli_exit_codes(monkeypatch, status, expected_code):
    monkeypatch.setattr(compat, "apply_disk_patch", lambda: status)
    monkeypatch.setattr(compat, "find_ogg_py", lambda: Path("/tmp/ogg.py"))
    assert compat.patch_cli() == expected_code
