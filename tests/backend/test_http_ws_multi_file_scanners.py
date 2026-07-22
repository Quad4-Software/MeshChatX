# SPDX-License-Identifier: 0BSD

"""Prove HTTP/WS contract scanners see routes under backend/http and lifecycle."""

from __future__ import annotations

from pathlib import Path

from tests.backend.http_api_contract_helpers import (
    extract_meshchat_http_routes,
    http_route_source_paths,
)
from tests.backend.ws_contract_helpers import iter_ws_source_files

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MESHCHAT_PY = _REPO_ROOT / "meshchatx" / "meshchat.py"
_HTTP_ROOT = _REPO_ROOT / "meshchatx" / "src" / "backend" / "http"
_LIFECYCLE_ROOT = _REPO_ROOT / "meshchatx" / "src" / "backend" / "lifecycle"


def test_http_route_source_paths_include_meshchat_and_http_package(tmp_path):
    repo = tmp_path / "repo"
    meshchat = repo / "meshchatx"
    meshchat.mkdir(parents=True)
    (meshchat / "meshchat.py").write_text("# placeholder\n", encoding="utf-8")
    routes_dir = meshchat / "src" / "backend" / "http" / "routes"
    routes_dir.mkdir(parents=True)
    (routes_dir / "status.py").write_text(
        '@routes.get("/api/v1/status")\nasync def status(request):\n    return None\n',
        encoding="utf-8",
    )
    paths = http_route_source_paths(repo)
    assert (meshchat / "meshchat.py") in paths
    assert (routes_dir / "status.py") in paths


def test_extract_counts_routes_only_under_backend_http(tmp_path):
    repo = tmp_path / "repo"
    meshchat = repo / "meshchatx"
    meshchat.mkdir(parents=True)
    (meshchat / "meshchat.py").write_text(
        "# no routes here\n",
        encoding="utf-8",
    )
    routes_dir = meshchat / "src" / "backend" / "http" / "routes"
    routes_dir.mkdir(parents=True)
    (routes_dir / "shell.py").write_text(
        '@routes.get("/")\n'
        "async def index(request):\n"
        "    return None\n"
        "\n"
        '@routes.get("/api/v1/example-only-in-http")\n'
        "async def example(request):\n"
        "    return None\n",
        encoding="utf-8",
    )
    live = extract_meshchat_http_routes(meshchat / "meshchat.py")
    assert {"method": "GET", "path": "/"} in live
    assert {"method": "GET", "path": "/api/v1/example-only-in-http"} in live


def test_http_route_source_paths_includes_live_backend_http():
    files = http_route_source_paths(_REPO_ROOT)
    assert _MESHCHAT_PY in files
    assert any(
        _HTTP_ROOT in path.parents or path.parent == _HTTP_ROOT for path in files
    )


def test_live_meshchat_routes_still_discovered():
    live = extract_meshchat_http_routes(_MESHCHAT_PY)
    assert any(r["path"] == "/api/v1/status" for r in live)
    assert any(r["path"] == "/" for r in live)


def test_iter_ws_source_files_includes_backend_http_and_lifecycle():
    files = iter_ws_source_files(_REPO_ROOT)
    assert _MESHCHAT_PY in files
    assert any("backend/http" in path.as_posix() for path in files)
    if _LIFECYCLE_ROOT.is_dir():
        assert any("backend/lifecycle" in path.as_posix() for path in files)
