# SPDX-License-Identifier: 0BSD
"""Warm macOS x64 venv cache still needs openssl@3 dylibs on the runner."""

from __future__ import annotations

import re
from pathlib import Path

_OPENSSL_SCRIPT = Path("scripts/ci/github-ensure-macos-x64-openssl.sh")
_WORKFLOWS = (
    Path(".github/workflows/native-build-dev.yml"),
    Path(".github/workflows/build-release.yml"),
)
_OPENSSL_STEP = re.compile(
    r"- name: Ensure openssl@3 for cx_Freeze x64 slice\n"
    r"              if: (?P<when>[^\n]+)\n"
    r"              run: bash scripts/ci/github-ensure-macos-x64-openssl.sh",
)


def test_openssl_script_requires_libssl_dylib() -> None:
    text = _OPENSSL_SCRIPT.read_text(encoding="utf-8")
    assert "/usr/local/opt/openssl@3/lib/libssl.3.dylib" in text
    assert "github-ensure-macos-x86-64-homebrew.sh" in text
    assert "--build-from-source" not in text


def test_macos_workflows_install_openssl_on_warm_venv_cache() -> None:
    for path in _WORKFLOWS:
        text = path.read_text(encoding="utf-8")
        match = _OPENSSL_STEP.search(text)
        assert match, f"missing openssl ensure step in {path}"
        assert "x64_ready" not in match.group("when"), path
        assert match.group("when") == "matrix.label == 'macos'"
