# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from meshchatx.src.backend.bake_frozen_pycodec2 import (
    bake_frozen_pycodec2,
    _is_codec2_lib,
    _pick_source_lib,
)

_VERIFY = Path("scripts/ci/github-verify-frozen-codec2.sh")


@pytest.fixture(autouse=True)
def _ignore_host_pycodec2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2._pycodec2_dist_dir",
        lambda: None,
    )


def _frozen_pycodec2_tree(tmp_path: Path) -> Path:
    pkg = tmp_path / "lib" / "pycodec2"
    pkg.mkdir(parents=True)
    (pkg / "pycodec2.cpython-314-darwin.so").write_bytes(b"so")
    (pkg / "__init__.py").write_text("from .pycodec2 import *\n", encoding="utf-8")
    return tmp_path


def test_is_codec2_lib_accepts_versioned_names() -> None:
    assert _is_codec2_lib("libcodec2.1.2.dylib") is True
    assert _is_codec2_lib("libcodec2.dylib") is True
    assert _is_codec2_lib("libcodec2.so.1.2") is True
    assert _is_codec2_lib("libcodec2.dll") is True
    assert _is_codec2_lib("pycodec2.cpython-314-darwin.so") is False
    assert _is_codec2_lib("libother.dylib") is False


def test_pick_source_lib_prefers_canonical_dylib_name(tmp_path: Path) -> None:
    versioned = tmp_path / "libcodec2.1.2.dylib"
    canonical = tmp_path / "libcodec2.dylib"
    versioned.write_bytes(b"v")
    canonical.write_bytes(b"c")
    picked = _pick_source_lib([versioned, canonical])
    assert picked == canonical


def test_bake_copies_dylibs_layout_to_canonical_and_executable_path(
    tmp_path: Path,
) -> None:
    root = _frozen_pycodec2_tree(tmp_path)
    pkg = root / "lib" / "pycodec2"
    dylibs = pkg / ".dylibs"
    dylibs.mkdir()
    (dylibs / "libcodec2.1.2.dylib").write_bytes(b"codec2-bytes")

    bake_frozen_pycodec2(root)

    assert (pkg / "libcodec2.dylib").read_bytes() == b"codec2-bytes"
    assert (root / "lib" / "libcodec2.dylib").read_bytes() == b"codec2-bytes"
    assert (root / "lib" / "libcodec2.1.2.dylib").read_bytes() == b"codec2-bytes"
    assert not dylibs.exists()


def test_bake_fails_when_libcodec2_missing_on_darwin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2.sys.platform", "darwin"
    )
    root = _frozen_pycodec2_tree(tmp_path)
    with pytest.raises(SystemExit, match="libcodec2 not found"):
        bake_frozen_pycodec2(root)


def test_bake_skips_missing_libcodec2_on_linux(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2.sys.platform", "linux"
    )
    root = _frozen_pycodec2_tree(tmp_path)
    bake_frozen_pycodec2(root)
    assert not (root / "lib" / "pycodec2" / "libcodec2.dylib").exists()


def test_bake_fails_when_pycodec2_package_missing(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    with pytest.raises(SystemExit, match="missing"):
        bake_frozen_pycodec2(tmp_path)


def test_bake_fails_when_extension_missing(tmp_path: Path) -> None:
    pkg = tmp_path / "lib" / "pycodec2"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match="no pycodec2 extension"):
        bake_frozen_pycodec2(tmp_path)


def test_bake_copies_executable_path_basename_from_load_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2.sys.platform", "darwin"
    )
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2._darwin_load_commands",
        lambda _ext: ["@executable_path/lib/libcodec2.1.2.dylib"],
    )
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2._rewrite_darwin_extension",
        lambda *_args, **_kwargs: None,
    )
    root = _frozen_pycodec2_tree(tmp_path)
    (root / "lib" / "pycodec2" / "libcodec2.dylib").write_bytes(b"lib")

    bake_frozen_pycodec2(root)

    assert (root / "lib" / "libcodec2.1.2.dylib").read_bytes() == b"lib"
    assert (root / "lib" / "libcodec2.dylib").read_bytes() == b"lib"


def test_bake_copies_from_build_env_when_freeze_tree_has_no_dylib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _frozen_pycodec2_tree(tmp_path)
    dist = tmp_path / "site" / "pycodec2"
    dist.mkdir(parents=True)
    (dist / "libcodec2.dylib").write_bytes(b"from-venv")
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_pycodec2._pycodec2_dist_dir",
        lambda: dist,
    )

    bake_frozen_pycodec2(root)

    assert (root / "lib" / "pycodec2" / "libcodec2.dylib").read_bytes() == b"from-venv"
    assert (root / "lib" / "libcodec2.dylib").read_bytes() == b"from-venv"


def test_verify_frozen_codec2_script_rejects_missing_extension(tmp_path: Path) -> None:
    (tmp_path / "lib" / "pycodec2").mkdir(parents=True)
    result = subprocess.run(
        ["bash", str(_VERIFY), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "no pycodec2 extension" in result.stderr


def test_verify_frozen_codec2_script_requires_dylib_on_darwin(tmp_path: Path) -> None:
    root = _frozen_pycodec2_tree(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uname = bin_dir / "uname"
    uname.write_text("#!/bin/sh\necho Darwin\n", encoding="utf-8")
    uname.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        ["bash", str(_VERIFY), str(root)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "libcodec2 missing" in result.stderr


def test_verify_frozen_codec2_script_accepts_extension(tmp_path: Path) -> None:
    root = _frozen_pycodec2_tree(tmp_path)
    (root / "lib" / "pycodec2" / "libcodec2.dylib").write_bytes(b"lib")
    result = subprocess.run(
        ["bash", str(_VERIFY), str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "frozen codec2 verify: OK" in result.stdout


def test_ci_wires_codec2_freeze_guards() -> None:
    deps = Path("scripts/ci/github-install-deps.sh").read_text(encoding="utf-8")
    x64 = Path("scripts/ci/github-install-macos-x64-python-deps.sh").read_text(
        encoding="utf-8"
    )
    universal = Path("scripts/build-macos-universal.sh").read_text(encoding="utf-8")
    backend_js = Path("scripts/build-backend.js").read_text(encoding="utf-8")
    probe = Path("meshchatx/src/backend/frozen_freeze_probe.py").read_text(
        encoding="utf-8"
    )
    unify = Path("scripts/unify-backend-plain-files.sh").read_text(encoding="utf-8")
    macos_ci = Path("scripts/ci/github-build-macos.sh").read_text(encoding="utf-8")
    windows_ci = Path("scripts/ci/github-build-windows.sh").read_text(encoding="utf-8")
    ci_yml = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "patch_lxst_codec2_optional.py" in deps
    assert "unify-backend may drop it later" not in deps
    assert "patch_lxst_codec2_optional.py" in x64
    assert "unify-backend may drop it later" not in x64
    assert "bake_frozen_pycodec2" in backend_js
    assert "github-verify-frozen-codec2.sh" in universal
    assert "github-verify-frozen-runtime.sh" in universal
    assert "github-verify-frozen-codec2.sh" in macos_ci
    assert "github-verify-frozen-codec2.sh" in windows_ci
    assert "github-verify-frozen-codec2.sh" in ci_yml
    assert "import LXST" in probe
    assert "import pycodec2" in probe
    assert "required native" in unify
    assert "libcodec2" in unify
