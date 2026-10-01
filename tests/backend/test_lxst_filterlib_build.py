# SPDX-License-Identifier: 0BSD

"""Tests for scripts/build-lxst-filterlib.py."""

import importlib.util
import shutil
import sysconfig
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build-lxst-filterlib.py"
_spec = importlib.util.spec_from_file_location("build_lxst_filterlib", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_artifact_name_matches_running_abi():
    if sysconfig.get_config_var("EXT_SUFFIX"):
        expected = f"filterlib{sysconfig.get_config_var('EXT_SUFFIX')}"
        assert mod._artifact_name() == expected
    else:
        assert mod._artifact_name().startswith("filterlib")


def test_noop_when_artifact_present(capsys):
    pytest.importorskip("LXST")
    lxst_root = mod._lxst_root()
    if lxst_root is None or not (lxst_root / mod._artifact_name()).is_file():
        pytest.skip("no filterlib artifact for this ABI")
    assert mod.main() == 0
    assert "present" in capsys.readouterr().out


def test_builds_loadable_library(tmp_path, monkeypatch):
    pytest.importorskip("LXST")
    if shutil.which("cc") is None and shutil.which("gcc") is None:
        pytest.skip("no C compiler")

    lxst_root = mod._lxst_root()
    src = lxst_root / "Filters.c"
    if not src.is_file():
        pytest.skip("LXST Filters.c not shipped")

    fake_root = tmp_path / "LXST"
    fake_root.mkdir()
    (fake_root / "Filters.c").write_bytes(src.read_bytes())

    artifact = fake_root / mod._artifact_name()
    monkeypatch.setattr(mod, "_lxst_root", lambda: fake_root)
    assert mod.main() == 0
    assert artifact.is_file()

    from cffi import FFI

    ffi = FFI()
    header = lxst_root / "Filters.h"
    ffi.cdef(header.read_text())
    lib = ffi.dlopen(str(artifact))
    out = ffi.new("float[]", 4)
    lib.lowpass_filter(
        ffi.new("float[]", [1.0, 1.0, 1.0, 1.0]),
        out,
        4,
        1,
        0.5,
        ffi.new("float[]", 1),
    )
    assert out[0] > 0.0
