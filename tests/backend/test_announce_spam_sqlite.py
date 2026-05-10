# SPDX-License-Identifier: 0BSD

"""SQLite integration: announce spam and bounded storage (anti-exhaustion).

Multi-minute soak scenarios live in ``test_long_running_stress.py`` (opt-in via
``MESHCHAT_LONG_TEST_SECONDS``).
"""

from __future__ import annotations

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


def test_spam_unique_destinations_stays_within_cap(sqlite_db):
    db, _path = sqlite_db
    cap = 48
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=cap)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    total = 650
    for i in range(total):
        dh = f"{i:032x}"
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{i:032x}"),
            bytes.fromhex(dh),
            "lxmf.delivery",
            b"x",
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == cap


def test_spam_same_destination_does_not_duplicate_rows(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=12)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()
    dest = bytes.fromhex("ab" * 16)
    ident = _FakeIdentity("cd" * 16)

    for _ in range(400):
        mgr.upsert_announce(ret, ident, dest, "lxmf.delivery", b"y", None)

    rows = db.provider.fetchall(
        "SELECT COUNT(*) AS n FROM announces WHERE aspect = ? AND destination_hash = ?",
        ("lxmf.delivery", "ab" * 16),
    )
    assert rows[0]["n"] == 1
    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 1


def test_spam_interleaved_aspects_each_bounded(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(
        announce_max_stored_lxmf_delivery=15,
        announce_max_stored_nomadnetwork_node=9,
        announce_max_stored_lxmf_propagation=11,
    )
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    for round_i in range(120):
        i = round_i * 3
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{i + 1:032x}"),
            bytes.fromhex(f"{i + 1:032x}"),
            "lxmf.delivery",
            b"a",
            None,
        )
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{i + 2:032x}"),
            bytes.fromhex(f"{i + 2:032x}"),
            "nomadnetwork.node",
            b"b",
            None,
        )
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{i + 3:032x}"),
            bytes.fromhex(f"{i + 3:032x}"),
            "lxmf.propagation",
            b"c",
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 15
    assert db.announces.get_announce_count_by_aspect("nomadnetwork.node") == 9
    assert db.announces.get_announce_count_by_aspect("lxmf.propagation") == 11


def test_quick_check_ok_after_heavy_announce_spam(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=30)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()

    for i in range(900):
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{i % 100:032x}"),
            bytes.fromhex(f"{i:032x}"),
            "lxmf.delivery",
            os.urandom(64),
            None,
        )

    qc = db.provider.quick_check()
    assert qc
    first = qc[0]
    val = next(iter(first.values()))
    assert val == "ok"


def test_large_app_data_spam_remains_bounded(sqlite_db):
    db, _path = sqlite_db
    cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=20)
    mgr = AnnounceManager(db, cfg)
    ret = MagicMock()
    blob = b"z" * 12000

    for i in range(180):
        mgr.upsert_announce(
            ret,
            _FakeIdentity(f"{i:032x}"),
            bytes.fromhex(f"{i:032x}"),
            "lxmf.delivery",
            blob,
            None,
        )

    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 20
