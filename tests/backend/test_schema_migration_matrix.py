# SPDX-License-Identifier: 0BSD

"""Upgrade matrix: open schema_v{N-1} and schema_v{N-2} fixtures, run Database.initialize()."""

from __future__ import annotations

import json
import shutil
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.database import (
    Database,
    DatabaseTooNewError,
    PostMigrationVerificationError,
)
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "schema_versions"
MANIFEST = FIXTURE_DIR / "manifest.json"


@pytest.fixture(autouse=True)
def reset_provider():
    DatabaseProvider._instance = None
    yield
    if DatabaseProvider._instance is not None:
        DatabaseProvider._instance.close_all()
    DatabaseProvider._instance = None


def _fixture_path(version: int) -> Path:
    path = FIXTURE_DIR / f"schema_v{version}.db"
    if not path.is_file():
        pytest.skip(
            f"Missing fixture {path}; run scripts/ci/schema_fixture_generate.py"
        )
    return path


def test_manifest_matches_latest_version():
    if not MANIFEST.is_file():
        pytest.skip("schema fixture manifest missing")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert int(data["latest_version"]) == DatabaseSchema.LATEST_VERSION


@pytest.mark.parametrize(
    "offset",
    [1, 2],
    ids=["n_minus_1", "n_minus_2"],
)
def test_fixture_upgrades_to_latest(tmp_path, offset):
    target_fixture = DatabaseSchema.LATEST_VERSION - offset
    if target_fixture < 1:
        pytest.skip("No fixture for this offset")
    src = _fixture_path(target_fixture)
    db_path = tmp_path / "live.db"
    shutil.copy2(src, db_path)
    db = Database(str(db_path))
    db.initialize()
    row = db.provider.fetchone(
        "SELECT value FROM config WHERE key = ?",
        ("database_version",),
    )
    assert int(row["value"]) == DatabaseSchema.LATEST_VERSION
    rows = db.provider.quick_check()
    assert (
        rows
        and (rows[0][0] if not isinstance(rows[0], dict) else list(rows[0].values())[0])
        == "ok"
    )
    db.close_all()


def test_fixture_upgrade_writes_pre_migrate_backup(tmp_path):
    ver = DatabaseSchema.LATEST_VERSION - 1
    if ver < 1:
        pytest.skip("No N-1 fixture")
    src = _fixture_path(ver)
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    db_path = identity_dir / "database.db"
    shutil.copy2(src, db_path)
    db = Database(str(db_path))
    db.initialize()
    backups = db.list_auto_backups(str(identity_dir))
    db.close_all()
    assert any("backup-pre-migrate" in b["name"] for b in backups)


def test_post_migration_verify_failure_blocks_version_bump(tmp_path):
    db_path = tmp_path / "verify.db"
    db = Database(str(db_path))
    db.schema._create_initial_tables()
    prior = DatabaseSchema.LATEST_VERSION - 1
    if prior < 1:
        pytest.skip("No prior version")
    db.schema.migrate_up_to(prior)
    with patch.object(
        db.provider, "quick_check", return_value=[{"quick_check": "fail"}]
    ):
        with pytest.raises(PostMigrationVerificationError):
            db.initialize()
    row = db.provider.fetchone(
        "SELECT value FROM config WHERE key = ?",
        ("database_version",),
    )
    assert int(row["value"]) == prior
    db.close_all()


def test_database_too_new_refuses_initialize(tmp_path):
    db_path = tmp_path / "new.db"
    db = Database(str(db_path))
    db.schema._create_initial_tables()
    future = DatabaseSchema.LATEST_VERSION + 1
    db.provider.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("database_version", str(future)),
    )
    with pytest.raises(DatabaseTooNewError):
        db.initialize()
    db.close_all()


@settings(
    deadline=None,
    max_examples=40,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    bogus=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=0,
        max_size=12,
    ),
)
def test_bogus_database_version_config_does_not_crash_initialize(bogus):
    if bogus.strip().isdigit():
        bogus = "x"
    dir_path = tempfile.mkdtemp()
    db_path = os.path.join(dir_path, "bogus.db")
    db = Database(str(db_path))
    db.schema._create_initial_tables()
    db.provider.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("database_version", bogus),
    )
    try:
        db.initialize()
    except (ValueError, PostMigrationVerificationError, DatabaseTooNewError):
        pass
    finally:
        db.close_all()
