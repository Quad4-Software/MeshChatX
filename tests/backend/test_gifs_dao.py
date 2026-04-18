# SPDX-License-Identifier: 0BSD

"""Tests for UserGifsDAO and schema migration for user_gifs."""

import base64

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    database = Database(str(path))
    database.initialize()
    assert DatabaseSchema.LATEST_VERSION >= 45
    return database


def _tiny_gif():
    return b"GIF89a" + b"\x00" * 32


def _tiny_webp():
    return b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


def test_insert_and_list(db):
    identity = "ab" * 16
    raw = _tiny_gif()
    row = db.gifs.insert(identity, "one", "gif", raw, None)
    assert row is not None
    assert row["id"] >= 1
    assert row["usage_count"] == 0
    assert row["last_used_at"] is None
    listed = db.gifs.list_for_identity(identity)
    assert len(listed) == 1
    assert listed[0]["image_size"] == len(raw)


def test_insert_webp_ok(db):
    identity = "ee" * 16
    row = db.gifs.insert(identity, "w", "webp", _tiny_webp(), None)
    assert row["image_type"] == "webp"


def test_duplicate_returns_none(db):
    identity = "cd" * 16
    raw = _tiny_gif()
    r1 = db.gifs.insert(identity, None, "gif", raw, None)
    assert r1 is not None
    r2 = db.gifs.insert(identity, None, "gif", raw, None)
    assert r2 is None
    assert db.gifs.count_for_identity(identity) == 1


def test_record_usage_orders_by_most_used(db):
    identity = "11" * 16
    a = db.gifs.insert(identity, "a", "gif", _tiny_gif(), None)
    b = db.gifs.insert(identity, "b", "gif", _tiny_gif() + b"x", None)
    c = db.gifs.insert(identity, "c", "gif", _tiny_gif() + b"y", None)
    db.gifs.record_usage(b["id"], identity)
    db.gifs.record_usage(b["id"], identity)
    db.gifs.record_usage(c["id"], identity)
    rows = db.gifs.list_for_identity(identity)
    ids = [r["id"] for r in rows]
    # b (2 uses), c (1 use), a (0 uses)
    assert ids == [b["id"], c["id"], a["id"]]
    by_id = {r["id"]: r for r in rows}
    assert by_id[b["id"]]["usage_count"] == 2
    assert by_id[c["id"]]["usage_count"] == 1
    assert by_id[a["id"]]["usage_count"] == 0
    assert by_id[b["id"]]["last_used_at"] is not None


def test_record_usage_wrong_identity(db):
    identity = "01" * 16
    other = "02" * 16
    row = db.gifs.insert(identity, None, "gif", _tiny_gif(), None)
    assert db.gifs.record_usage(row["id"], other) is False


def test_delete_and_delete_all(db):
    identity = "ef" * 16
    db.gifs.insert(identity, "a", "gif", _tiny_gif(), None)
    row = db.gifs.list_for_identity(identity)[0]
    assert db.gifs.delete(row["id"], identity) is True
    assert len(db.gifs.list_for_identity(identity)) == 0

    db.gifs.insert(identity, "b", "gif", _tiny_gif(), None)
    db.gifs.insert(identity, "c", "gif", _tiny_gif() + b"x", None)
    n = db.gifs.delete_all_for_identity(identity)
    assert n == 2
    assert db.gifs.count_for_identity(identity) == 0


def test_get_row_image_blob(db):
    identity = "aa" * 16
    raw = _tiny_gif()
    ins = db.gifs.insert(identity, "n", "gif", raw, "msg1")
    full = db.gifs.get_row(ins["id"], identity)
    assert full["image_blob"] == raw
    assert full["source_message_hash"] == "msg1"


def test_update_name(db):
    identity = "bb" * 16
    ins = db.gifs.insert(identity, "old", "gif", _tiny_gif(), None)
    assert db.gifs.update_name(ins["id"], identity, "new") is True
    row = db.gifs.get_row(ins["id"], identity)
    assert row["name"] == "new"


def test_export_and_import_roundtrip(db):
    identity = "cc" * 16
    raw = _tiny_gif()
    ins = db.gifs.insert(identity, "a", "gif", raw, None)
    db.gifs.record_usage(ins["id"], identity)
    payloads = db.gifs.export_payloads_for_identity(identity)
    assert len(payloads) == 1
    assert base64.b64decode(payloads[0]["image_bytes"]) == raw
    assert payloads[0]["usage_count"] == 1

    other = "dd" * 16
    items = [
        {
            "name": "x",
            "image_type": "gif",
            "image_bytes_b64": payloads[0]["image_bytes"],
            "source_message_hash": None,
            "usage_count": 7,
        },
    ]
    r = db.gifs.import_payloads(other, items, replace_duplicates=False)
    assert r["imported"] == 1
    rows = db.gifs.list_for_identity(other)
    assert len(rows) == 1
    assert rows[0]["usage_count"] == 7
    r2 = db.gifs.import_payloads(other, items, replace_duplicates=False)
    assert r2["skipped_duplicates"] == 1


def test_import_invalid_base64_skipped(db):
    identity = "ff" * 16
    items = [
        {
            "name": "x",
            "image_type": "gif",
            "image_bytes_b64": "!!!not-base64!!!",
            "source_message_hash": None,
        },
    ]
    r = db.gifs.import_payloads(identity, items, replace_duplicates=False)
    assert r["skipped_invalid"] >= 1


def test_gif_limit(db, monkeypatch):
    from meshchatx.src.backend import gif_utils

    monkeypatch.setattr(gif_utils, "MAX_GIFS_PER_IDENTITY", 2)
    identity = "22" * 16
    db.gifs.insert(identity, None, "gif", _tiny_gif(), None)
    db.gifs.insert(identity, None, "gif", _tiny_gif() + b"y", None)
    with pytest.raises(ValueError, match="gif_limit_reached"):
        db.gifs.insert(identity, None, "gif", _tiny_gif() + b"z", None)
