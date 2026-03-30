"""Contract tests: aiohttp routes in meshchat.py vs checked-in manifest; frontend /api/v1 usage."""

import os
from pathlib import Path

import pytest

from tests.backend.http_api_contract_helpers import (
    extract_frontend_api_paths,
    extract_meshchat_http_routes,
    load_route_fixture,
    path_matches_aiohttp_route,
    write_route_fixture,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MESHCHAT_PY = _REPO_ROOT / "meshchatx" / "meshchat.py"
_FRONTEND_ROOT = _REPO_ROOT / "meshchatx" / "src" / "frontend"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "http_api_routes.json"


def test_meshchat_http_routes_match_fixture():
    live = extract_meshchat_http_routes(_MESHCHAT_PY)
    if os.environ.get("UPDATE_HTTP_API_ROUTES") == "1":
        write_route_fixture(_FIXTURE, live)
        pytest.skip("UPDATE_HTTP_API_ROUTES=1: fixture updated; re-run without the env var")
    expected = load_route_fixture(_FIXTURE)
    assert live == expected, (
        "HTTP route list drifted. If you added or renamed routes, run: "
        "UPDATE_HTTP_API_ROUTES=1 poetry run pytest tests/backend/test_http_api_contract.py -k "
        "meshchat_http_routes_match_fixture"
    )


def test_frontend_api_paths_exist_on_backend():
    backend_paths = [r["path"] for r in extract_meshchat_http_routes(_MESHCHAT_PY)]
    frontend_paths = extract_frontend_api_paths(_FRONTEND_ROOT)
    missing = []
    for fp in sorted(frontend_paths):
        if not any(path_matches_aiohttp_route(br, fp) for br in backend_paths):
            missing.append(fp)
    assert not missing, f"Frontend references unknown HTTP paths: {missing}"
