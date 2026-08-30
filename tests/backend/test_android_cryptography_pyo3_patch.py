# SPDX-License-Identifier: 0BSD

"""Chaquopy cryptography-50 pyo3 patch must apply to the 50.0.0 sdist Cargo.toml."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATCH = (
    ROOT
    / "android"
    / "chaquopy-recipes"
    / "cryptography-50"
    / "patches"
    / "pyo3_no_interpreter.patch"
)
META = ROOT / "android" / "chaquopy-recipes" / "cryptography-50" / "meta.yaml"

# cryptography-50.0.0 sdist Cargo.toml (PyPI tarball).
CARGO_TOML_50_0_0 = """\
[workspace]
resolver = "2"
members = [
    "src/rust/",
    "src/rust/cryptography-cffi",
    "src/rust/cryptography-crypto",
    "src/rust/cryptography-keepalive",
    "src/rust/cryptography-key-parsing",
    "src/rust/cryptography-openssl",
    "src/rust/cryptography-x509",
    "src/rust/cryptography-x509-verification",
]

[workspace.package]
version = "0.50.0"
authors = ["The cryptography developers <cryptography-dev@python.org>"]
edition = "2021"
publish = false
# This specifies the MSRV
rust-version = "1.83.0"
license = "Apache-2.0 OR BSD-3-Clause"

[workspace.dependencies]
asn1 = { version = "0.24.1", default-features = false }
base64 = "0.23"
cc = "1.2.63"
cfg-if = "1"
foreign-types = "0.3"
foreign-types-shared = "0.1"
openssl = "0.10.80"
openssl-sys = "0.9.116"
pem = { version = "4", default-features = false }
pyo3 = { version = "0.29", features = ["abi3", "abi3t"] }
pyo3-build-config = { version = "0.29" }
self_cell = "1"

[profile.release]
overflow-checks = true
"""


@pytest.mark.skipif(shutil.which("patch") is None, reason="patch is required")
def test_pyo3_no_interpreter_patch_applies_to_cryptography_50_0_0(
    tmp_path: Path,
) -> None:
    assert META.read_text(encoding="utf-8").count('version: "50.0.0"') == 1
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(CARGO_TOML_50_0_0, encoding="utf-8")
    result = subprocess.run(
        ["patch", "-p1", "-i", str(PATCH)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    patched = cargo.read_text(encoding="utf-8")
    assert (
        patched.count(
            'pyo3 = { version = "0.29", features = ["abi3", "abi3t", "abi3-py310"] }',
        )
        == 1
    )
    assert (
        patched.count('pyo3 = { version = "0.29", features = ["abi3", "abi3t"] }') == 0
    )
