# SPDX-License-Identifier: 0BSD

"""Tests for UserStickerPacksDAO and pack/sticker association."""

import pytest

from meshchatx.src.backend.database import Database


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    database = Database(str(path))
    database.initialize()
    return database


def _tiny_png():
    return bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * 32


def test_create_and_list_packs(db):
    identity = "aa" * 16
    pack = db.sticker_packs.insert(
        identity,
        "Cats",
        short_name="cats",
        description="furry",
        pack_type="static",
    )
    assert pack["id"] >= 1
    assert pack["title"] == "Cats"
    assert pack["short_name"] == "cats"
    rows = db.sticker_packs.list_for_identity(identity)
    assert len(rows) == 1
    assert rows[0]["title"] == "Cats"


def test_short_name_unique_per_identity(db):
    identity = "bb" * 16
    db.sticker_packs.insert(identity, "A", short_name="dup")
    with pytest.raises(ValueError, match="duplicate_pack_short_name"):
        db.sticker_packs.insert(identity, "B", short_name="dup")


def test_short_name_scoped_to_identity(db):
    a = "11" * 16
    b = "22" * 16
    db.sticker_packs.insert(a, "A", short_name="shared")
    db.sticker_packs.insert(b, "B", short_name="shared")
    assert db.sticker_packs.count_for_identity(a) == 1
    assert db.sticker_packs.count_for_identity(b) == 1


def test_update_pack(db):
    identity = "cc" * 16
    pack = db.sticker_packs.insert(identity, "Old")
    ok = db.sticker_packs.update(
        pack["id"],
        identity,
        title="New",
        description="desc",
        pack_type="animated",
    )
    assert ok is True
    row = db.sticker_packs.get_row(pack["id"], identity)
    assert row["title"] == "New"
    assert row["description"] == "desc"
    assert row["pack_type"] == "animated"


def test_delete_detaches_stickers(db):
    identity = "dd" * 16
    pack = db.sticker_packs.insert(identity, "P")
    sticker = db.stickers.insert(
        identity,
        "s",
        "png",
        _tiny_png(),
        None,
        pack_id=pack["id"],
    )
    assert sticker is not None
    assert db.sticker_packs.delete(pack["id"], identity) is True
    full = db.stickers.get_row(sticker["id"], identity)
    assert full is not None
    assert full["pack_id"] is None


def test_delete_with_stickers_removes_them(db):
    identity = "ee" * 16
    pack = db.sticker_packs.insert(identity, "P")
    sticker = db.stickers.insert(
        identity,
        "s",
        "png",
        _tiny_png(),
        None,
        pack_id=pack["id"],
    )
    assert sticker is not None
    assert db.sticker_packs.delete_with_stickers(pack["id"], identity) is True
    assert db.stickers.get_row(sticker["id"], identity) is None


def test_reorder(db):
    identity = "ff" * 16
    a = db.sticker_packs.insert(identity, "A")
    b = db.sticker_packs.insert(identity, "B")
    c = db.sticker_packs.insert(identity, "C")
    n = db.sticker_packs.reorder(identity, [c["id"], a["id"], b["id"]])
    assert n == 3
    rows = db.sticker_packs.list_for_identity(identity)
    assert [r["title"] for r in rows] == ["C", "A", "B"]


def test_assign_to_pack(db):
    identity = "01" * 16
    pack = db.sticker_packs.insert(identity, "P")
    sticker = db.stickers.insert(identity, "s", "png", _tiny_png(), None)
    assert db.stickers.assign_to_pack(sticker["id"], identity, pack["id"]) is True
    rows = db.stickers.list_for_pack(pack["id"], identity)
    assert len(rows) == 1
    assert db.stickers.assign_to_pack(sticker["id"], identity, None) is True
    assert db.stickers.list_for_pack(pack["id"], identity) == []


def test_export_and_install_pack_roundtrip(db):
    identity = "02" * 16
    other = "03" * 16
    pack = db.sticker_packs.insert(identity, "Pack", short_name="pack")
    db.stickers.insert(identity, "s", "png", _tiny_png(), None, pack_id=pack["id"])

    payloads = db.stickers.export_payloads_for_pack(pack["id"], identity)
    assert len(payloads) == 1

    new_pack = db.sticker_packs.insert(other, "Pack")
    items = [
        {
            "name": p["name"],
            "image_type": p["image_type"],
            "image_bytes_b64": p["image_bytes"],
            "emoji": p.get("emoji"),
        }
        for p in payloads
    ]
    r = db.stickers.import_payloads(
        other,
        items,
        replace_duplicates=False,
        pack_id=new_pack["id"],
    )
    assert r["imported"] == 1
    rows = db.stickers.list_for_pack(new_pack["id"], other)
    assert len(rows) == 1
