# SPDX-License-Identifier: 0BSD

"""Helpers for HTTP API route contract checks (meshchat.py and backend/http)."""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROUTE_DECORATOR = re.compile(
    r'@routes\.(get|post|patch|delete|put)\(\s*(?:\n\s*)?["\']([^"\']+)["\']',
    re.MULTILINE,
)


def http_route_source_paths(repo_root: Path) -> list[Path]:
    """Return source files that may declare aiohttp route decorators."""
    paths: list[Path] = [repo_root / "meshchatx" / "meshchat.py"]
    http_root = repo_root / "meshchatx" / "src" / "backend" / "http"
    if http_root.is_dir():
        paths.extend(sorted(http_root.rglob("*.py")))
    return [p for p in paths if p.is_file()]


def extract_meshchat_http_routes(meshchat_py: Path) -> list[dict[str, str]]:
    """Extract route method/path pairs from meshchat.py and backend/http.

    meshchat_py may be the meshchat.py path or any path under the repo.
    The repo root is derived from a meshchatx/ parent when present.
    """
    meshchat_py = Path(meshchat_py)
    repo_root = meshchat_py
    for parent in [meshchat_py, *meshchat_py.parents]:
        if (parent / "meshchatx" / "meshchat.py").is_file():
            repo_root = parent
            break
        if parent.name == "meshchatx" and (parent / "meshchat.py").is_file():
            repo_root = parent.parent
            break

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in http_route_source_paths(repo_root):
        text = path.read_text(encoding="utf-8")
        for m in _ROUTE_DECORATOR.finditer(text):
            key = (m.group(1).upper(), m.group(2))
            if key in seen:
                continue
            seen.add(key)
            rows.append({"method": key[0], "path": key[1]})
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
        json.dumps({"routes": routes}, indent=4) + "\n",
        encoding="utf-8",
    )
