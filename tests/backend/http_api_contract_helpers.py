"""Helpers for HTTP API route contract checks (meshchat.py vs frontend)."""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROUTE_DECORATOR = re.compile(
    r'@routes\.(get|post|patch|delete|put)\(\s*(?:\n\s*)?["\']([^"\']+)["\']',
    re.MULTILINE,
)


def extract_meshchat_http_routes(meshchat_py: Path) -> list[dict[str, str]]:
    text = meshchat_py.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    for m in _ROUTE_DECORATOR.finditer(text):
        rows.append({"method": m.group(1).upper(), "path": m.group(2)})
    rows.sort(key=lambda x: (x["path"], x["method"]))
    return rows


def path_matches_aiohttp_route(route: str, path: str) -> bool:
    pattern = ""
    i = 0
    while i < len(route):
        if route[i] == "{":
            j = route.find("}", i)
            if j == -1:
                return False
            pattern += "[^/]+"
            i = j + 1
        else:
            pattern += re.escape(route[i])
            i += 1
    return re.fullmatch(pattern, path) is not None


def extract_frontend_api_paths(frontend_root: Path) -> set[str]:
    out: set[str] = set()
    for path in list(frontend_root.rglob("*.vue")) + list(frontend_root.rglob("*.js")):
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"`(/api/v1[^`]+)`", text):
            s = m.group(1).split("?")[0]
            s = re.sub(r"\$\{[^}]+\}", "a", s)
            out.add(s)
        for m in re.finditer(r'["\'](/api/v1[^"\']+)["\']', text):
            s = m.group(1).split("?")[0]
            if "${" in s:
                continue
            out.add(s)
    return out


def load_route_fixture(fixture_path: Path) -> list[dict[str, str]]:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    routes = data["routes"]
    routes.sort(key=lambda x: (x["path"], x["method"]))
    return routes


def write_route_fixture(fixture_path: Path, routes: list[dict[str, str]]) -> None:
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps({"routes": routes}, indent=2) + "\n",
        encoding="utf-8",
    )
