# SPDX-License-Identifier: 0BSD

"""Static OpenAPI core contract vs aiohttp route fixture."""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.backend.http_api_contract_helpers import load_route_fixture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPENAPI = _REPO_ROOT / "openapi" / "meshchatx-ui-core.yaml"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "http_api_routes.json"


def _load_openapi_ops() -> list[tuple[str, str]]:
    doc = yaml.safe_load(_OPENAPI.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    paths = doc.get("paths") or {}
    ops: list[tuple[str, str]] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                ops.append((method.upper(), path))
    ops.sort(key=lambda x: (x[1], x[0]))
    return ops


def test_openapi_core_file_exists():
    assert _OPENAPI.is_file(), f"missing {_OPENAPI}"


def test_openapi_core_paths_exist_on_backend_fixture():
    routes = {(r["method"], r["path"]) for r in load_route_fixture(_FIXTURE)}
    missing = []
    for method, path in _load_openapi_ops():
        if (method, path) not in routes:
            missing.append(f"{method} {path}")
    assert not missing, (
        "OpenAPI core paths missing from http_api_routes.json: " + ", ".join(missing)
    )


def test_openapi_core_has_auth_mutators():
    ops = set(_load_openapi_ops())
    for required in (
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/setup"),
        ("PATCH", "/api/v1/config"),
        ("GET", "/api/v1/auth/csrf"),
        ("GET", "/api/v1/status"),
    ):
        assert required in ops, f"expected {required} in core OpenAPI"


def test_openapi_core_parses_as_openapi_31():
    doc = yaml.safe_load(_OPENAPI.read_text(encoding="utf-8"))
    assert str(doc.get("openapi", "")).startswith("3.")
    assert "paths" in doc and "components" in doc
