# SPDX-License-Identifier: 0BSD

"""Helpers for the backend module ownership contract.

Parses the "Backend" table in .agents/module-ownership.md into a plain
row structure, and resolves the backtick-quoted spans in that table to
on-disk paths under meshchatx/src/backend/ or
meshchatx/src/frontend/components/. Prose cells without backtick spans
(for example "(none)" or "App shell banners") resolve to an empty list,
since they describe behaviour rather than referencing a concrete file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BACKEND_ROOT = "meshchatx/src/backend"
FRONTEND_COMPONENTS_ROOT = "meshchatx/src/frontend/components"
FRONTEND_ROOT = "meshchatx/src/frontend"

_HEADER_KEY_MAP = {
    "domain": "domain",
    "manager modules": "manager_modules",
    "http route module": "http_route_module",
    "ws module": "ws_module",
    "primary tests": "primary_tests",
    "frontend page": "frontend_page",
}

_CODE_SPAN_RE = re.compile(r"`([^`]+)`")


def _split_row(line: str) -> list[str]:
    cells = line.strip().split("|")
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def _code_spans(cell: str) -> list[str]:
    return _CODE_SPAN_RE.findall(cell)


def parse_backend_ownership_table(doc_path: Path) -> list[dict]:
    """Parse the Backend markdown table into a list of row dicts.

    Each row maps header keys to lists of backtick-quoted spans, except
    "domain" which maps to the plain cell text. Only the pipe table found
    directly under the "## Backend" heading is parsed.
    """
    lines = doc_path.read_text(encoding="utf-8").splitlines()

    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Backend":
            start = i + 1
            break
    if start is None:
        raise ValueError("Backend section heading not found in module-ownership.md")

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    table_lines = [line for line in lines[start:end] if line.strip().startswith("|")]
    if len(table_lines) < 2:
        raise ValueError("Backend table not found under the Backend heading")

    header = [h.lower() for h in _split_row(table_lines[0])]
    keys = [_HEADER_KEY_MAP[h] for h in header]

    rows = []
    for line in table_lines[2:]:
        cells = _split_row(line)
        row = {}
        for key, cell in zip(keys, cells):
            row[key] = cell if key == "domain" else _code_spans(cell)
        rows.append(row)
    return rows


def write_ownership_fixture(fixture_path: Path, rows: list[dict]) -> None:
    payload = {"version": 1, "domains": rows}
    fixture_path.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")


def load_ownership_fixture(fixture_path: Path) -> list[dict]:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload["domains"]


def _resolve_spans(
    spans: list[str],
    root: str,
    default_dir: str = "",
    carry_forward: bool = False,
) -> list[tuple[str, str]]:
    """Resolve backtick spans to (relative_path, kind) pairs, kind in {file, dir}.

    A span ending in "/*" or "/" is a directory reference. A span containing
    "/" is a fully qualified path and updates the carried directory. A bare
    filename resolves against the carried directory when carry_forward is
    set, otherwise against default_dir.
    """
    resolved: list[tuple[str, str]] = []
    current_dir = default_dir
    for span in spans:
        if span.endswith("/*"):
            rel_dir = span[:-2]
            resolved.append((f"{root}/{rel_dir}", "dir"))
            continue
        if span.endswith("/"):
            rel_dir = span[:-1]
            base = f"{root}/{current_dir}" if current_dir else root
            resolved.append((f"{base}/{rel_dir}", "dir"))
            continue
        if "/" in span:
            current_dir = span.rsplit("/", 1)[0]
            resolved.append((f"{root}/{span}", "file"))
            continue
        base_dir = current_dir if carry_forward else default_dir
        rel = f"{base_dir}/{span}" if base_dir else span
        resolved.append((f"{root}/{rel}", "file"))
    return resolved


def resolve_manager_module_paths(spans: list[str]) -> list[tuple[str, str]]:
    return _resolve_spans(spans, BACKEND_ROOT)


def resolve_http_route_paths(spans: list[str]) -> list[tuple[str, str]]:
    return _resolve_spans(spans, BACKEND_ROOT, default_dir="http/routes")


def resolve_ws_module_paths(spans: list[str]) -> list[tuple[str, str]]:
    return _resolve_spans(spans, BACKEND_ROOT)


def resolve_frontend_page_paths(spans: list[str]) -> list[tuple[str, str]]:
    """Resolve frontend page spans under components/, or features/ under frontend/."""
    resolved: list[tuple[str, str]] = []
    feature_spans: list[str] = []
    component_spans: list[str] = []
    for span in spans:
        if span.startswith("features/"):
            feature_spans.append(span)
        else:
            component_spans.append(span)
    resolved.extend(_resolve_spans(feature_spans, FRONTEND_ROOT))
    resolved.extend(
        _resolve_spans(component_spans, FRONTEND_COMPONENTS_ROOT, carry_forward=True),
    )
    return resolved
