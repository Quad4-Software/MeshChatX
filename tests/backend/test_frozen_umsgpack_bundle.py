# SPDX-License-Identifier: 0BSD
"""Oracle: frozen desktop builds must ship RNS.vendor.umsgpack (issue 76)."""

from __future__ import annotations

from pathlib import Path

_CX_SETUP = Path("cx_setup.py")
_VERIFY = Path("scripts/ci/github-verify-frozen-umsgpack.sh")
_PROBE = Path("meshchatx/src/backend/frozen_freeze_probe.py")


def test_cx_setup_includes_rns_vendor_umsgpack() -> None:
    src = _CX_SETUP.read_text(encoding="utf-8")
    assert '"RNS.vendor"' in src
    assert '"RNS.vendor.umsgpack"' in src


def test_frozen_freeze_probe_imports_umsgpack() -> None:
    src = _PROBE.read_text(encoding="utf-8")
    assert "import RNS.vendor.umsgpack as umsgpack" in src
    assert "umsgpack.packb" in src


def test_ci_wires_umsgpack_freeze_guard() -> None:
    assert _VERIFY.is_file()
    verify = _VERIFY.read_text(encoding="utf-8")
    assert "RNS.vendor.umsgpack" in verify

    ci_yml = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    macos_ci = Path("scripts/ci/github-build-macos.sh").read_text(encoding="utf-8")
    windows_ci = Path("scripts/ci/github-build-windows.sh").read_text(encoding="utf-8")
    universal = Path("scripts/build-macos-universal.sh").read_text(encoding="utf-8")

    assert "github-verify-frozen-umsgpack.sh" in ci_yml
    assert "github-verify-frozen-umsgpack.sh" in macos_ci
    assert "github-verify-frozen-umsgpack.sh" in windows_ci
    assert "github-verify-frozen-umsgpack.sh" in universal
