#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Fail when schema migrations contain destructive SQL without an explicit allow tag."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "meshchatx/src/backend/database/schema.py"
FIXTURE_MANIFEST = ROOT / "tests/backend/fixtures/schema_versions/manifest.json"

DESTRUCTIVE = re.compile(
    r"(DROP\s+TABLE|DROP\s+COLUMN|ALTER\s+TABLE\s+.+\s+RENAME)",
    re.IGNORECASE,
)
DELETE_FROM = re.compile(r"DELETE\s+FROM", re.IGNORECASE)
DEDUP_DELETE = re.compile(r"NOT\s+IN\s*\(\s*SELECT", re.IGNORECASE)
ALLOW_TAG = "migration-safety: allow-destructive"


def _run_migrations_source() -> str:
    text = SCHEMA.read_text(encoding="utf-8")
    marker = "def _run_migrations"
    start = text.index(marker)
    rest = text[start:]
    depth = 0
    end = len(rest)
    for i, ch in enumerate(rest):
        if ch == "\n" and rest[i : i + 4] == "\n    def " and depth == 0 and i > 20:
            end = i
            break
    return rest[:end]


def _check_schema_fixtures() -> list[str]:
    errors: list[str] = []
    if not FIXTURE_MANIFEST.is_file():
        errors.append(
            "schema fixture manifest missing; run task schema-fixtures",
        )
        return errors
    import json

    sys.path.insert(0, str(ROOT))
    from meshchatx.src.backend.database.schema import DatabaseSchema

    latest = DatabaseSchema.LATEST_VERSION
    data = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    if int(data.get("latest_version", -1)) != latest:
        errors.append(
            f"schema fixtures stale (manifest latest {data.get('latest_version')}, "
            f"code {latest}); run task schema-fixtures",
        )
    return errors


def main() -> int:
    if not SCHEMA.is_file():
        print(f"check_schema_migrations: missing {SCHEMA}", file=sys.stderr)
        return 1
    violations: list[str] = []
    for line in _run_migrations_source().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ALLOW_TAG in line:
            continue
        if DESTRUCTIVE.search(line):
            violations.append(stripped)
            continue
        if DELETE_FROM.search(line) and not DEDUP_DELETE.search(line):
            violations.append(stripped)
    if violations:
        print(
            "check_schema_migrations: destructive SQL in _run_migrations "
            f"(prefer expand-only migrations or add {ALLOW_TAG} on the line):",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    fixture_errors = _check_schema_fixtures()
    if fixture_errors:
        print("check_schema_migrations:", file=sys.stderr)
        for err in fixture_errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
