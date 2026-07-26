# SPDX-License-Identifier: 0BSD
"""Oracles for map drawing ownership (identity_hash column)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "map_drawings_oracle.db")
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    database = Database(path)
    yield database
    database.close_all()
    provider.close_all()


def test_oracle_delete_drawing_scoped_to_identity_hash(db):
    owner_a = "aa" * 16
    owner_b = "bb" * 16
    now = datetime.now(UTC)
    db.provider.execute(
        """
        INSERT INTO map_drawings (identity_hash, name, data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (owner_a, "a-line", "{}", now, now),
    )
    row_b = db.provider.execute(
        """
        INSERT INTO map_drawings (identity_hash, name, data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (owner_b, "b-line", "{}", now, now),
    )
    drawing_b_id = row_b.lastrowid

    assert db.map_drawings.delete_drawing(drawing_b_id, owner_a) is False
    assert len(db.map_drawings.get_drawings(owner_b)) == 1
    assert db.map_drawings.delete_drawing(drawing_b_id, owner_b) is True
    assert db.map_drawings.get_drawings(owner_b) == []


def test_oracle_update_drawing_scoped_to_identity_hash(db):
    owner_a = "cc" * 16
    owner_b = "dd" * 16
    now = datetime.now(UTC)
    db.provider.execute(
        """
        INSERT INTO map_drawings (identity_hash, name, data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (owner_a, "shared-name", '{"a":1}', now, now),
    )
    row_b = db.provider.execute(
        """
        INSERT INTO map_drawings (identity_hash, name, data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (owner_b, "b-shape", '{"b":1}', now, now),
    )
    drawing_b_id = row_b.lastrowid

    assert (
        db.map_drawings.update_drawing(
            drawing_b_id,
            owner_a,
            "hijacked",
            '{"x":1}',
        )
        is False
    )
    rows = db.map_drawings.get_drawings(owner_b)
    assert len(rows) == 1
    assert rows[0]["name"] == "b-shape"

    assert (
        db.map_drawings.update_drawing(
            drawing_b_id,
            owner_b,
            "renamed",
            '{"b":2}',
        )
        is True
    )
    rows = db.map_drawings.get_drawings(owner_b)
    assert rows[0]["name"] == "renamed"
