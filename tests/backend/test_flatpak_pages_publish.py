# SPDX-License-Identifier: 0BSD
"""Tests for the GitHub Pages flatpak publish path."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PUBLISH = _REPO / "scripts" / "ci" / "github-publish-flatpak-pages.sh"
_SIZE_CHECK = _REPO / "scripts" / "ci" / "check_pages_size.py"
_CHANNEL = _REPO / "scripts" / "ci" / "github_flatpak_channel.py"


def _load_channel():
    spec = importlib.util.spec_from_file_location("github_flatpak_channel", _CHANNEL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _repo_base_url(owner_repo: str) -> str:
    env = dict(os.environ)
    env.pop("FLATPAK_REPO_BASE_URL", None)
    env["GITHUB_REPOSITORY"] = owner_repo
    env["GITHUB_TOKEN"] = "x"
    env["GITHUB_REF_NAME"] = "v0.0.0"
    # Probe only the URL derivation: the publish script prints the resolved
    # base URL before it needs a bundle or network. Feed a missing bundle so
    # it exits after printing, and scrape the printed line.
    proc = subprocess.run(
        ["bash", str(_PUBLISH), "/nonexistent/none.flatpak"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    out = proc.stdout + proc.stderr
    for line in out.splitlines():
        if "Flatpak repo base URL:" in line:
            return line.split("Flatpak repo base URL:", 1)[1].strip()
    raise AssertionError(f"no base URL printed: {out}")


def test_repo_base_url_derived_from_github_repository() -> None:
    assert (
        _repo_base_url("Quad4-Software/MeshChatX")
        == "https://quad4-software.github.io/MeshChatX/flatpak"
    )


def test_repo_base_url_lowercases_owner_only() -> None:
    assert _repo_base_url("MiXeD/My-Repo") == "https://mixed.github.io/My-Repo/flatpak"


def test_flatpak_branch_mapping() -> None:
    mod = _load_channel()
    fn = mod.flatpak_branch_from_ref_name
    assert fn("v4.10.8") == "stable"
    assert fn("beta-2025.1") == "beta"
    assert fn("preview-1") == "beta"
    assert fn("nightly-2025.1.1") == "testing"
    assert fn("testing-1") == "testing"


def test_check_pages_size_passes_small_tree(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"x" * 128)
    proc = subprocess.run(
        ["python3", str(_SIZE_CHECK), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "total" in proc.stdout


def test_check_pages_size_rejects_oversized_file(tmp_path: Path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(b"0")
    with open(big, "r+b") as f:
        f.truncate(96 * 1024 * 1024)
    proc = subprocess.run(
        ["python3", str(_SIZE_CHECK), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 1
    assert "big.bin" in proc.stderr


def test_check_pages_size_rejects_missing_dir() -> None:
    proc = subprocess.run(
        ["python3", str(_SIZE_CHECK), str(_REPO / "no-such-dir")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
