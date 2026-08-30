# SPDX-License-Identifier: 0BSD

"""Contract test: .agents/module-ownership.md Backend table vs files on disk.

Parses the Backend table directly from the doc so the checked-in fixture
drifts loudly (via a failing diff) whenever a row is added, removed, or
retyped, then asserts every manager module, HTTP route module, WS module,
and frontend page path referenced by the table actually exists. Primary
tests cells are prose-heavy, so only glob-like spans are checked, and only
one matching test file per row is required since a row often lists several
loosely related test names.
"""

import glob
import os
from pathlib import Path

import pytest

from tests.backend.module_ownership_contract_helpers import (
    load_ownership_fixture,
    parse_backend_ownership_table,
    resolve_frontend_page_paths,
    resolve_http_route_paths,
    resolve_manager_module_paths,
    resolve_ws_module_paths,
    write_ownership_fixture,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC_PATH = _REPO_ROOT / ".agents" / "module-ownership.md"
_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "backend_module_ownership.json"
)
_TESTS_BACKEND_DIR = Path(__file__).resolve().parent


def test_backend_ownership_table_matches_fixture():
    parsed = parse_backend_ownership_table(_DOC_PATH)
    if os.environ.get("UPDATE_BACKEND_MODULE_OWNERSHIP") == "1":
        write_ownership_fixture(_FIXTURE, parsed)
        pytest.skip(
            "UPDATE_BACKEND_MODULE_OWNERSHIP=1: fixture updated; re-run without the env var",
        )
    expected = load_ownership_fixture(_FIXTURE)
    assert parsed == expected, (
        "Backend module ownership table drifted from the checked-in fixture. "
        "If the .agents/module-ownership.md Backend table changed on purpose, run: "
        "UPDATE_BACKEND_MODULE_OWNERSHIP=1 uv run pytest tests/backend/test_module_ownership_contract.py -k "
        "backend_ownership_table_matches_fixture"
    )


def _assert_paths_exist(rows: list[dict], key: str, resolver, label: str) -> None:
    for row in rows:
        for rel_path, kind in resolver(row[key]):
            full = _REPO_ROOT / rel_path
            exists = full.is_dir() if kind == "dir" else full.is_file()
            assert exists, f"{row['domain']}: {label} path missing on disk: {rel_path}"


def test_manager_modules_exist_on_disk():
    rows = load_ownership_fixture(_FIXTURE)
    _assert_paths_exist(
        rows,
        "manager_modules",
        resolve_manager_module_paths,
        "manager module",
    )


def test_http_route_modules_exist_on_disk():
    rows = load_ownership_fixture(_FIXTURE)
    _assert_paths_exist(
        rows,
        "http_route_module",
        resolve_http_route_paths,
        "HTTP route module",
    )


def test_ws_modules_exist_on_disk():
    rows = load_ownership_fixture(_FIXTURE)
    _assert_paths_exist(rows, "ws_module", resolve_ws_module_paths, "WS module")


def test_frontend_pages_exist_on_disk():
    rows = load_ownership_fixture(_FIXTURE)
    _assert_paths_exist(
        rows,
        "frontend_page",
        resolve_frontend_page_paths,
        "frontend page",
    )


def _looks_like_test_glob(span: str) -> bool:
    return span.startswith("test_")


def test_primary_tests_glob_patterns_match_at_least_one_file():
    rows = load_ownership_fixture(_FIXTURE)
    for row in rows:
        globs = [span for span in row["primary_tests"] if _looks_like_test_glob(span)]
        if not globs:
            continue
        matched = []
        for pattern in globs:
            matched.extend(
                glob.glob(str(_TESTS_BACKEND_DIR / "**" / pattern), recursive=True),
            )
        assert matched, (
            f"{row['domain']}: none of {globs} matched a file under tests/backend/"
        )
