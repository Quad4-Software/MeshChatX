# SPDX-License-Identifier: 0BSD

"""Shell routes: service worker Cache-Control for update discovery."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL_PY = ROOT / "meshchatx" / "src" / "backend" / "http" / "routes" / "shell.py"


def test_service_worker_route_sets_revalidate_cache_control() -> None:
    source = SHELL_PY.read_text(encoding="utf-8")
    assert 'path=app.get_public_path("service-worker.js")' in source
    assert '"Cache-Control": "no-cache, max-age=0, must-revalidate"' in source


def test_index_html_remains_no_store() -> None:
    source = SHELL_PY.read_text(encoding="utf-8")
    assert '"Cache-Control": "no-cache, no-store"' in source
