# SPDX-License-Identifier: 0BSD

"""Helpers for the schema version fixture manifest contract check."""

from __future__ import annotations

import json
from pathlib import Path


def derive_schema_versions_manifest(latest_version: int) -> dict[str, str]:
    """Return the manifest entries expected for a given latest schema version.

    Mirrors the fixture selection in scripts/ci/schema_fixture_generate.py:
    the latest version plus up to two prior versions when they exist.
    """
    versions = [latest_version]
    if latest_version >= 1:
        versions.append(latest_version - 1)
    if latest_version >= 2:
        versions.append(latest_version - 2)
    versions = sorted(set(versions))

    manifest: dict[str, str] = {"latest_version": str(latest_version)}
    for ver in versions:
        manifest[f"v{ver}"] = f"schema_v{ver}.db"
    return manifest


def load_schema_versions_manifest(fixture_path: Path) -> dict[str, str]:
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def write_schema_versions_manifest(
    fixture_path: Path, manifest: dict[str, str]
) -> None:
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
