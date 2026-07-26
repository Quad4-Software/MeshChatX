#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Generate schema_v{N}.db fixtures for migration matrix tests."""

from __future__ import annotations

import json
from pathlib import Path

from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests/backend/fixtures/schema_versions"
MANIFEST = FIXTURE_DIR / "manifest.json"


def main() -> int:
    latest = DatabaseSchema.LATEST_VERSION
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    versions = [latest]
    if latest >= 1:
        versions.append(latest - 1)
    if latest >= 2:
        versions.append(latest - 2)
    versions = sorted(set(versions))

    manifest: dict[str, str] = {"latest_version": str(latest)}
    for ver in versions:
        db_path = FIXTURE_DIR / f"schema_v{ver}.db"
        if db_path.exists():
            db_path.unlink()
        provider = DatabaseProvider(str(db_path))
        schema = DatabaseSchema(provider)
        schema._create_initial_tables()
        schema.migrate_up_to(ver)
        provider.close_all()
        manifest[f"v{ver}"] = db_path.name

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote fixtures for versions {versions} under {FIXTURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
