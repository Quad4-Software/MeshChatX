# SPDX-License-Identifier: 0BSD
"""macOS x64 native dependencies include OpenSSL via MacPorts."""

from __future__ import annotations

import re
from pathlib import Path

# The native-build-dev workflow now uses MacPorts on a GitHub-hosted
# macos-15-intel runner because Homebrew no longer supports Intel macOS.
_NATIVE_DEPS_SCRIPT = Path("scripts/ci/github-install-macos-x64-port-deps.sh")
_NATIVE_BUILD_DEV = Path(".github/workflows/native-build-dev.yml")
_DEPS_STEP = re.compile(
    r"- name: Install x64 macOS native dependencies\n"
    r"              if: matrix.label == 'macos-x64'\n"
    r"              run: bash scripts/ci/github-install-macos-x64-port-deps.sh",
)


def test_macos_x64_deps_script_installs_openssl() -> None:
    """The x64 dependency script must install OpenSSL from MacPorts."""
    text = _NATIVE_DEPS_SCRIPT.read_text(encoding="utf-8")
    assert "sudo port -N install" in text, "expected MacPorts install command"
    assert "openssl" in text, "expected openssl to be installed via MacPorts"
    assert 'OPENSSL_DIR="/opt/local"' in text, "expected MacPorts OpenSSL prefix"
    assert 'OPENSSL_LIB_DIR="/opt/local/lib"' in text, "expected MacPorts lib path"
    assert 'OPENSSL_INCLUDE_DIR="/opt/local/include"' in text, "expected MacPorts include path"


def test_macos_workflows_install_openssl_on_x64() -> None:
    """The native-build-dev workflow must run the x64 MacPorts deps script."""
    text = _NATIVE_BUILD_DEV.read_text(encoding="utf-8")
    match = _DEPS_STEP.search(text)
    assert match, "missing x64 macOS native dependency step"
