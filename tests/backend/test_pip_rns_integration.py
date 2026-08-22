# SPDX-License-Identifier: 0BSD

"""Tests for optional pip-rns / rngit dependency helpers."""

from __future__ import annotations

import importlib.util
import json
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
        pinned_rns="9.9.9",
    )
    assert count == 2
    assert (dest / "index.html").is_file()
    assert (dest / "manual" / "index.html").is_file()
    assert not (dest / "manual.pdf").exists()
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["rns_version"] == "9.9.9"


def test_pinned_rns_version_reads_uv_lock():
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_pin_test")
    version = fetch.pinned_rns_version(_REPO / "uv.lock")
    assert version is not None
    assert version.count(".") >= 1


def test_should_skip_fetch_when_bundle_matches_rns_version(tmp_path):
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_skip_test")
    dest = tmp_path / "out"
    manual = dest / "manual"
    manual.mkdir(parents=True)
    (manual / "index.html").write_text("<html>m</html>", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    source = fetch.DEFAULT_RNS_SOURCE
    manifest.write_text(
        json.dumps(
            {
                "source_url": source,
                "rns_version": "1.5.0",
            }
        ),
        encoding="utf-8",
    )
    skip, reason = fetch.should_skip_fetch(
        dest=dest,
        manifest_path=manifest,
        source_url=source,
        pinned_rns="1.5.0",
        force=False,
    )
    assert skip is True
    assert "match" in reason


def test_should_not_skip_fetch_when_rns_version_changes(tmp_path):
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_stale_test")
    dest = tmp_path / "out"
    manual = dest / "manual"
    manual.mkdir(parents=True)
    (manual / "index.html").write_text("<html>m</html>", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    source = fetch.DEFAULT_RNS_SOURCE
    manifest.write_text(
        json.dumps(
            {
                "source_url": source,
                "rns_version": "1.4.0",
            }
        ),
        encoding="utf-8",
    )
    skip, reason = fetch.should_skip_fetch(
        dest=dest,
        manifest_path=manifest,
        source_url=source,
        pinned_rns="1.5.0",
        force=False,
    )
    assert skip is False
    assert "rns version changed" in reason


def test_default_docs_source_is_rngit_website():
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_default_test")
    assert fetch.DEFAULT_SOURCES == (fetch.DEFAULT_RNS_SOURCE,)
    assert fetch.DEFAULT_RNS_SOURCE.startswith("rns://")
    assert fetch.DEFAULT_RNS_SOURCE.endswith("/reticulum/website")


def test_taskfile_has_pip_rns_targets():
    text = (_REPO / "Taskfile.yml").read_text(encoding="utf-8")
    assert "deps:backend:rns:" in text
    assert "docs:rns:" in text
    assert "scripts/pip-rns-deps.sh" in text
