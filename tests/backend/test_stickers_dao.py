"""Tests for UserStickersDAO and schema migration for user_stickers."""

import base64

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.schema import DatabaseSchema


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    database = Database(str(path))
    database.initialize()
    assert DatabaseSchema.LATEST_VERSION >= 44
    return database


def _tiny_png():
    return bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * 32


def test_insert_and_list(db):
    identity = "ab" * 16
    raw = _tiny_png()
    row = db.stickers.insert(identity, "one", "png", raw, None)
    assert row is not None
    assert row["id"] >= 1
    listed = db.stickers.list_for_identity(identity)
    assert len(listed) == 1
    assert listed[0]["image_size"] == len(raw)


def test_duplicate_returns_none(db):
    identity = "cd" * 16
    raw = _tiny_png()
    r1 = db.stickers.insert(identity, None, "png", raw, None)
    assert r1 is not None
    r2 = db.stickers.insert(identity, None, "png", raw, None)
    assert r2 is None
    assert db.stickers.count_for_identity(identity) == 1


def test_delete_and_delete_all(db):
    identity = "ef" * 16
    db.stickers.insert(identity, "a", "png", _tiny_png(), None)
    row = db.stickers.list_for_identity(identity)[0]
    assert db.stickers.delete(row["id"], identity) is True
    assert len(db.stickers.list_for_identity(identity)) == 0

    db.stickers.insert(identity, "b", "png", _tiny_png(), None)
    db.stickers.insert(
        identity,
        "c",
        "png",
        _tiny_png() + b"x",
        None,
    )
    n = db.stickers.delete_all_for_identity(identity)
    assert n == 2
    assert db.stickers.count_for_identity(identity) == 0


def test_wrong_identity_delete(db):
    identity = "01" * 16
    other = "02" * 16
    row = db.stickers.insert(identity, None, "png", _tiny_png(), None)
    assert db.stickers.delete(row["id"], other) is False


def test_get_row_image_blob(db):
    identity = "aa" * 16
    raw = _tiny_png()
    ins = db.stickers.insert(identity, "n", "png", raw, "msg1")
    full = db.stickers.get_row(ins["id"], identity)
    assert full["image_blob"] == raw
    assert full["source_message_hash"] == "msg1"


def test_update_name(db):
    identity = "bb" * 16
    ins = db.stickers.insert(identity, "old", "png", _tiny_png(), None)
    assert db.stickers.update_name(ins["id"], identity, "new") is True
    row = db.stickers.get_row(ins["id"], identity)
    assert row["name"] == "new"


def test_export_and_import_roundtrip(db):
    identity = "cc" * 16
    raw = _tiny_png()
    db.stickers.insert(identity, "a", "png", raw, None)
    payloads = db.stickers.export_payloads_for_identity(identity)
    assert len(payloads) == 1
    assert base64.b64decode(payloads[0]["image_bytes"]) == raw

    other = "dd" * 16
    items = [
        {
            "name": "x",
            "image_type": "png",
            "image_bytes_b64": payloads[0]["image_bytes"],
            "source_message_hash": None,
        },
    ]
    r = db.stickers.import_payloads(other, items, replace_duplicates=False)
    assert r["imported"] == 1
    assert db.stickers.count_for_identity(other) == 1
    r2 = db.stickers.import_payloads(other, items, replace_duplicates=False)
    assert r2["skipped_duplicates"] == 1


def test_import_replace_duplicate(db):
    identity = "ee" * 16
    raw = _tiny_png()
    db.stickers.insert(identity, "first", "png", raw, None)
    items = [
        {
            "name": "second",
            "image_type": "png",
            "image_bytes_b64": base64.b64encode(raw).decode("ascii"),
            "source_message_hash": None,
        },
    ]
    r = db.stickers.import_payloads(identity, items, replace_duplicates=True)
    assert r["imported"] == 1
    rows = db.stickers.list_for_identity(identity)
    assert len(rows) == 1
    assert rows[0]["name"] == "second"


def test_import_invalid_base64_skipped(db):
    identity = "ff" * 16
    items = [
        {
            "name": "x",
            "image_type": "png",
            "image_bytes_b64": "!!!not-base64!!!",
            "source_message_hash": None,
        },
    ]
    r = db.stickers.import_payloads(identity, items, replace_duplicates=False)
    assert r["skipped_invalid"] >= 1


def test_sticker_limit(db, monkeypatch):
    from meshchatx.src.backend import sticker_utils

    monkeypatch.setattr(sticker_utils, "MAX_STICKERS_PER_IDENTITY", 2)
    identity = "11" * 16
    db.stickers.insert(identity, None, "png", _tiny_png(), None)
    db.stickers.insert(identity, None, "png", _tiny_png() + b"y", None)
    with pytest.raises(ValueError, match="sticker_limit"):
        db.stickers.insert(identity, None, "png", _tiny_png() + b"z", None)
