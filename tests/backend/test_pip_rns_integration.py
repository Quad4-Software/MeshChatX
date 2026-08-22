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
    assert fetch.DEFAULT_SOURCES[0] == fetch.DEFAULT_RNS_SOURCE
    assert fetch.DEFAULT_HTTPS_FALLBACK in fetch.DEFAULT_SOURCES
    assert fetch.DEFAULT_RNS_SOURCE.startswith("rns://")
    assert fetch.DEFAULT_RNS_SOURCE.endswith("/reticulum/website")


def test_should_skip_fetch_accepts_https_fallback_manifest(tmp_path):
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_https_skip_test")
    dest = tmp_path / "out"
    manual = dest / "manual"
    manual.mkdir(parents=True)
    (manual / "index.html").write_text("<html>m</html>", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source_url": fetch.DEFAULT_HTTPS_FALLBACK,
                "rns_version": "1.5.0",
            }
        ),
        encoding="utf-8",
    )
    skip, reason = fetch.should_skip_fetch(
        dest=dest,
        manifest_path=manifest,
        source_url=fetch.DEFAULT_RNS_SOURCE,
        pinned_rns="1.5.0",
        force=False,
    )
    assert skip is True
    assert "match" in reason


def test_parse_mcx_tcp_bootstraps_filters_clearnet_online():
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_mcx_parse_test")
    payload = {
        "interfaces": [
            {
                "name": "Good TCP",
                "type": "tcp",
                "network": "clearnet",
                "status": "online",
                "host": "rns.example.test",
                "port": 4242,
            },
            {
                "name": "Ygg",
                "type": "tcp",
                "network": "yggdrasil",
                "status": "online",
                "host": "200::1",
                "port": 4242,
            },
            {
                "name": "Offline",
                "type": "tcp",
                "network": "clearnet",
                "status": "offline",
                "host": "offline.example.test",
                "port": 4242,
            },
        ],
    }
    rows = fetch._parse_mcx_tcp_bootstraps(payload)
    assert len(rows) == 1
    assert rows[0].host == "rns.example.test"
    assert rows[0].port == 4242


def test_write_bootstrap_config(tmp_path):
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_bootstrap_cfg_test")
    config_path = tmp_path / "config"
    fetch._write_bootstrap_config(
        config_path,
        [
            fetch.TcpBootstrap(name="Node A", host="a.example.test", port=4242),
            fetch.TcpBootstrap(name="Node B", host="b.example.test", port=4343),
        ],
    )
    text = config_path.read_text(encoding="utf-8")
    assert "type = TCPClientInterface" in text
    assert "target_host = a.example.test" in text
    assert "bootstrap_only = yes" in text
    assert "RNS_CONFIG" not in text


def test_pick_random_tcp_bootstraps_uses_sample(monkeypatch):
    fetch = _load_module(_FETCH, "fetch_reticulum_manual_bootstrap_pick_test")
    pool = [
        fetch.TcpBootstrap(name=f"Node {i}", host=f"h{i}.test", port=4000 + i)
        for i in range(6)
    ]
    monkeypatch.setattr(fetch, "_fetch_mcx_tcp_bootstraps", lambda **kwargs: pool)
    picked = fetch._pick_random_tcp_bootstraps(
        3,
        timeout=5.0,
        rng=__import__("random").Random(0),
    )
    assert len(picked) == 3
    assert len({(p.host, p.port) for p in picked}) == 3


def test_taskfile_has_pip_rns_targets():
    text = (_REPO / "Taskfile.yml").read_text(encoding="utf-8")
    assert "deps:backend:rns:" in text
    assert "docs:rns:" in text
    assert "scripts/pip-rns-deps.sh" in text
