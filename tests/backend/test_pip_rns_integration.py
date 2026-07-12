# SPDX-License-Identifier: 0BSD

"""Tests for optional pip-rns / rngit dependency helpers."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "pip-rns-deps.sh"
_ALIASES = _REPO / "scripts" / "pip-rns" / "aliases"
_REMOTES = _REPO / "scripts" / "pip_rns_remotes.py"
_FETCH = _REPO / "scripts" / "build" / "fetch_reticulum_manual.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_pip_rns_deps_script_exists_and_is_executable():
    assert _SCRIPT.is_file()
    assert os.access(_SCRIPT, os.X_OK)


def test_pip_rns_deps_bash_syntax():
    subprocess.run(["bash", "-n", str(_SCRIPT)], check=True)


def test_pip_rns_deps_help():
    proc = subprocess.run(
        ["bash", str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "pip-rns" in proc.stdout


def test_pip_rns_deps_dry_run():
    proc = subprocess.run(
        ["bash", str(_SCRIPT), "--dry-run", "--skip-ensure"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(_REPO),
    )
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert "pip-rns install --uv rns" in out
    assert "pip-rns install --uv lxmf" in out
    assert "pip-rns install --uv lxst" in out


def test_aliases_file_has_markqvist_remotes():
    text = _ALIASES.read_text(encoding="utf-8")
    assert "7649a50d84610232d1416b41d2896aff/reticulum/reticulum" in text
    assert "7649a50d84610232d1416b41d2896aff/reticulum/lxmf" in text
    assert "7649a50d84610232d1416b41d2896aff/reticulum/lxst" in text
    assert "7649a50d84610232d1416b41d2896aff/reticulum/website" in text


def test_pip_rns_remotes_helpers():
    remotes = _load_module(_REMOTES, "pip_rns_remotes_under_test")
    aliases = remotes.parse_aliases(_ALIASES)
    assert aliases["rns"].endswith("/reticulum/reticulum")
    assert remotes.remote_url("lxmf", aliases).startswith("rns://")
    assert remotes.website_docs_source(aliases).startswith("rns://")
    assert "website" in remotes.website_docs_source(aliases)


def test_fetch_manual_from_local_docs_tree(tmp_path):
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_under_test")
    src = tmp_path / "website"
    docs = src / "docs"
    docs.mkdir(parents=True)
    (docs / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    (docs / "manual").mkdir()
    (docs / "manual" / "index.html").write_text("<html>m</html>", encoding="utf-8")
    (docs / "manual.pdf").write_bytes(b"%PDF")

    dest = tmp_path / "out"
    manifest = tmp_path / "manifest.json"
    count = fetch.fetch_manual(
        sources=[str(src)],
        dest=dest,
        force=True,
        include_pdf=False,
        manifest_path=manifest,
    )
    assert count == 2
    assert (dest / "index.html").is_file()
    assert (dest / "manual" / "index.html").is_file()
    assert not (dest / "manual.pdf").exists()
    assert manifest.is_file()


def test_taskfile_has_pip_rns_targets():
    text = (_REPO / "Taskfile.yml").read_text(encoding="utf-8")
    assert "deps:backend:rns:" in text
    assert "docs:rns:" in text
    assert "scripts/pip-rns-deps.sh" in text
