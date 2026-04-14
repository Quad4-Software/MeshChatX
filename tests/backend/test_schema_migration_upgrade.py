"""Upgrade path: simulate database at version N-1 and assert migration to LATEST_VERSION."""

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


def _column_names(provider, table: str) -> set[str]:
    cur = provider.connection.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}
    finally:
        cur.close()


@pytest.mark.skipif(
    DatabaseSchema.LATEST_VERSION < 41,
    reason="Test targets migration block for version 41",
)
def test_migrate_from_version_40_restores_attachments_stripped(tmp_path):
    """Version 41 adds lxmf_messages.attachments_stripped; re-apply from 40."""
    db_path = tmp_path / "mig.db"
    provider = DatabaseProvider(str(db_path))
    schema = DatabaseSchema(provider)
    schema.initialize()
    assert (
        int(
            provider.fetchone(
                "SELECT value FROM config WHERE key = ?",
                ("database_version",),
            )["value"],
        )
        == DatabaseSchema.LATEST_VERSION
    )

    provider.execute(
        "UPDATE config SET value = ? WHERE key = ?",
        ("40", "database_version"),
    )
    try:
        provider.execute("ALTER TABLE lxmf_messages DROP COLUMN attachments_stripped")
    except Exception as exc:
        pytest.skip(f"SQLite DROP COLUMN not available or failed: {exc}")

    assert "attachments_stripped" not in _column_names(provider, "lxmf_messages")

    schema.migrate(schema._get_current_version())

    assert "attachments_stripped" in _column_names(provider, "lxmf_messages")
    assert (
        int(
            provider.fetchone(
                "SELECT value FROM config WHERE key = ?",
                ("database_version",),
            )["value"],
        )
        == DatabaseSchema.LATEST_VERSION
    )

    provider.close_all()
