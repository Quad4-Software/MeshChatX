# SPDX-License-Identifier: 0BSD

"""Integration tests: announce row caps via AnnounceManager + real SQLite."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider


class _FakeIdentity:
    __slots__ = ("_h",)

    def __init__(self, identity_hex32: str):
        self._h = bytes.fromhex(identity_hex32)

    @property
    def hash(self):
        return self._h

    def get_public_key(self):
        return b"\xaa\xbb"


def _cleanup(db, path):
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
    DatabaseProvider._instance = None
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass
        for suffix in ("-wal", "-shm"):
            try:
                os.unlink(path + suffix)
            except OSError:
                pass


def _new_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = Database(path)
    db.initialize()
    return db, path


def _store_enabled_config(**max_stored):
    """Config mock with storage toggles on and configurable announce_max_stored_* .get() values."""
    config = MagicMock()
    for _k in (
        "announce_store_lxmf_delivery",
        "announce_store_lxst_telephony",
        "announce_store_nomadnetwork_node",
        "announce_store_lxmf_propagation",
        "announce_store_git_repositories",
    ):
        m = MagicMock()
        m.get.return_value = True
        setattr(config, _k, m)

    for key, default in (
        ("announce_max_stored_lxmf_delivery", None),
        ("announce_max_stored_nomadnetwork_node", None),
        ("announce_max_stored_lxmf_propagation", None),
    ):
        attr = MagicMock()
        attr.get.return_value = max_stored.get(key, default)
        setattr(config, key, attr)

    return config


@pytest.fixture
def sqlite_db():
    db, path = _new_db()
    yield db, path
    _cleanup(db, path)


def test_many_sequential_upserts_trims_to_max(sqlite_db):
    db, _path = sqlite_db
    max_keep = 12
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=max_keep)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    n_insert = 55
    for i in range(n_insert):
        dh = f"{i:032x}"
        ident = _FakeIdentity(f"{i:032x}")
        mgr.upsert_announce(
            ret,
            ident,
            bytes.fromhex(dh),
            "lxmf.delivery",
            b"payload",
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == max_keep
    rows = db.announces.get_announces(aspect="lxmf.delivery")
    kept = {r["destination_hash"] for r in rows}
    expect = {f"{i:032x}" for i in range(n_insert - max_keep, n_insert)}
    assert kept == expect


def test_aspect_max_limits_are_independent(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(
        announce_max_stored_lxmf_delivery=7,
        announce_max_stored_nomadnetwork_node=4,
    )
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    for i in range(20):
        dh = f"{i:032x}"
        ident = _FakeIdentity(f"{i:032x}")
        mgr.upsert_announce(
            ret,
            ident,
            bytes.fromhex(dh),
            "lxmf.delivery",
            b"x",
            None,
        )

    for i in range(15):
        dh = f"{0x70000000 + i:032x}"
        ident = _FakeIdentity(f"{0x71000000 + i:032x}")
        mgr.upsert_announce(
            ret,
            ident,
            bytes.fromhex(dh),
            "nomadnetwork.node",
            b"y",
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 7
    assert db.announces.get_announce_count_by_aspect("nomadnetwork.node") == 4


def test_repeated_upsert_same_destination_does_not_expand_table(sqlite_db):
    db, _path = sqlite_db
    max_keep = 10
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=max_keep)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    primary_dest = "f" * 32
    ident = _FakeIdentity("e" * 32)

    for _ in range(80):
        mgr.upsert_announce(
            ret,
            ident,
            bytes.fromhex(primary_dest),
            "lxmf.delivery",
            b"v1",
            None,
        )

    for i in range(25):
        dh = f"{i:032x}"
        oid = _FakeIdentity(f"1{i:031x}")
        mgr.upsert_announce(
            ret,
            oid,
            bytes.fromhex(dh),
            "lxmf.delivery",
            b"x",
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == max_keep
    dup_rows = db.provider.fetchall(
        """
        SELECT destination_hash FROM announces WHERE aspect = ?
        GROUP BY destination_hash HAVING COUNT(*) > 1
        """,
        ("lxmf.delivery",),
    )
    assert dup_rows == []


def test_manager_trim_skips_contact_linked_identity(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=500)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    protected_idx = 3
    contact_ih = f"{protected_idx:032x}"

    for i in range(8):
        dh = f"{i:032x}"
        ident = _FakeIdentity(f"{i:032x}")
        mgr.upsert_announce(
            ret,
            ident,
            bytes.fromhex(dh),
            "lxmf.delivery",
            b"p",
            None,
        )

    db.contacts.add_contact("peer", contact_ih)

    cfg.announce_max_stored_lxmf_delivery.get.return_value = 3
    mgr.upsert_announce(
        ret,
        _FakeIdentity("ffffffffffffffffffffffffffffffff"),
        bytes.fromhex("ffffffffffffffffffffffffffffffff"),
        "lxmf.delivery",
        b"tick",
        None,
    )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 3
    rows = db.announces.get_announces(aspect="lxmf.delivery")
    hashes = {r["destination_hash"] for r in rows}
    assert f"{protected_idx:032x}" in hashes


def test_trim_after_prefilled_table_overflow(sqlite_db):
    """Simulates a large announce backlog (direct DAO inserts), then one managed upsert."""
    db, _path = sqlite_db
    aspect = "lxmf.delivery"
    for i in range(220):
        dh = f"{i:032x}"
        db.announces.upsert_announce(
            {
                "destination_hash": dh,
                "aspect": aspect,
                "identity_hash": f"{i:032x}",
                "identity_public_key": "cHVibmtleQ==",
                "app_data": None,
                "rssi": None,
                "snr": None,
                "quality": None,
            },
        )

    assert db.announces.get_announce_count_by_aspect(aspect) == 220

    max_keep = 15
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=max_keep)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    mgr.upsert_announce(
        ret,
        _FakeIdentity("aa" * 16),
        bytes.fromhex(f"{220:032x}"),
        aspect,
        b"flush",
        None,
    )

    assert db.announces.get_announce_count_by_aspect(aspect) == max_keep
    kept = {r["destination_hash"] for r in db.announces.get_announces(aspect=aspect)}
    assert kept == {f"{i:032x}" for i in range(206, 221)}


def test_integration_respects_favourite_under_tight_cap(sqlite_db):
    db, _path = sqlite_db
    aspect = "lxmf.delivery"
    favourite_dest = f"{5:032x}"
    for i in range(24):
        dh = f"{i:032x}"
        db.announces.upsert_announce(
            {
                "destination_hash": dh,
                "aspect": aspect,
                "identity_hash": f"{i:032x}",
                "identity_public_key": "cHVibmtleQ==",
                "app_data": None,
                "rssi": None,
                "snr": None,
                "quality": None,
            },
        )

    db.announces.upsert_favourite(favourite_dest, "Pinned", aspect)

    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=4)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    mgr.upsert_announce(
        ret,
        _FakeIdentity("bb" * 16),
        bytes.fromhex(f"{100:032x}"),
        aspect,
        b"tight",
        None,
    )

    rows = db.announces.get_announces(aspect=aspect)
    hashes = {r["destination_hash"] for r in rows}
    assert favourite_dest in hashes
    assert f"{100:032x}" in hashes


def test_lxst_telephony_shares_lxmf_delivery_cap(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=6)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    for i in range(10):
        dh = f"{0x60000000 + i:032x}"
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{0x61000000 + i:032x}"),
            bytes.fromhex(dh),
            "lxst.telephony",
            b"t",
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxst.telephony") == 6
    kept = {
        r["destination_hash"]
        for r in db.announces.get_announces(aspect="lxst.telephony")
    }
    assert kept == {f"{0x60000000 + i:032x}" for i in range(4, 10)}
