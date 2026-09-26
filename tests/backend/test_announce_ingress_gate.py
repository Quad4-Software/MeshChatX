# SPDX-License-Identifier: 0BSD

"""Tests for the announce ingress gate and deferred write journal."""

import os
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.announce_manager import (
    ANNOUNCE_JOURNAL_MAX_PENDING,
    AnnounceManager,
    _norm_hash,
)
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
        for suffix in ("", "-wal", "-shm"):
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


@pytest.fixture
def sqlite_db():
    db, path = _new_db()
    yield db
    _cleanup(db, path)


def _peer_sets_db(
    contacts=(),
    favourites=(),
    peer_hashes=(),
    blocked=(),
):
    """MagicMock database whose fetchall answers the peer-set queries."""
    db = MagicMock()
    contact_rows = [
        {
            "remote_identity_hash": c[0],
            "lxmf_address": c[1] if len(c) > 1 else None,
            "lxst_address": c[2] if len(c) > 2 else None,
        }
        for c in contacts
    ]
    peer_rows = [{"peer_hash": h} for h in peer_hashes]

    def _fetchall(sql, params=None):
        if "FROM contacts" in sql:
            return contact_rows
        if "peer_hash FROM lxmf_messages" in sql:
            return peer_rows
        return []

    db.provider.fetchall.side_effect = _fetchall
    db.announces.get_favourites.return_value = [
        {"destination_hash": h} for h in favourites
    ]
    db.misc.get_blocked_destinations.return_value = [
        {"destination_hash": h} for h in blocked
    ]
    return db


def _ident(hex32):
    return _FakeIdentity(hex32)


class TestNormHash:
    def test_bytes_to_hex(self):
        assert _norm_hash(b"\xab\xcd") == "abcd"

    def test_hex_string_normalized(self):
        assert _norm_hash("ABCD") == "abcd"

    def test_none_is_empty(self):
        assert _norm_hash(None) == ""

    def test_strips_separators(self):
        assert _norm_hash("ab:cd") == "abcd"


class TestClassifyAnnounce:
    def test_contact_destination_is_priority(self):
        dh = "aa" * 16
        db = _peer_sets_db(contacts=[("cc" * 32, dh, None)])
        mgr = AnnounceManager(db)
        assert mgr.classify_announce(dh) == "priority"

    def test_contact_identity_is_priority(self):
        ih = "bb" * 32
        db = _peer_sets_db(contacts=[(ih, "dd" * 16, None)])
        mgr = AnnounceManager(db)
        assert mgr.classify_announce("ee" * 16, ih) == "priority"

    def test_favourite_is_priority(self):
        dh = "f0" * 16
        db = _peer_sets_db(favourites=[dh])
        mgr = AnnounceManager(db)
        assert mgr.classify_announce(dh) == "priority"

    def test_conversation_peer_is_priority(self):
        dh = "1a" * 16
        db = _peer_sets_db(peer_hashes=[dh])
        mgr = AnnounceManager(db)
        assert mgr.classify_announce(dh) == "priority"

    def test_stranger_is_background(self):
        db = _peer_sets_db()
        mgr = AnnounceManager(db)
        assert mgr.classify_announce("99" * 16, "88" * 32) == "background"

    def test_blocked_destination_is_blocked(self):
        dh = "de" * 16
        db = _peer_sets_db(blocked=[dh])
        mgr = AnnounceManager(db)
        assert mgr.classify_announce(dh) == "blocked"

    def test_blocked_related_hash_expansion(self):
        dh = "ab" * 16
        related = "cd" * 32
        db = _peer_sets_db(blocked=[dh])
        mgr = AnnounceManager(
            db,
            related_hashes_resolver=lambda h: [related] if h == dh else [],
        )
        assert mgr.classify_announce("ef" * 16, related) == "blocked"

    def test_blocked_beats_priority(self):
        dh = "aa" * 16
        db = _peer_sets_db(
            contacts=[("cc" * 32, dh, None)],
            blocked=[dh],
        )
        mgr = AnnounceManager(db)
        assert mgr.classify_announce(dh) == "blocked"

    def test_block_query_failure_fails_closed(self):
        db = _peer_sets_db()
        db.misc.get_blocked_destinations.side_effect = RuntimeError("db down")
        blocked_dh = "de" * 16
        mgr = AnnounceManager(
            db,
            is_blocked_resolver=lambda h: h == blocked_dh,
        )
        assert mgr.classify_announce(blocked_dh) == "blocked"
        assert mgr.classify_announce("aa" * 16) == "background"

    def test_block_resolver_exception_fails_closed(self):
        db = _peer_sets_db()
        db.misc.get_blocked_destinations.side_effect = RuntimeError("db down")
        mgr = AnnounceManager(
            db,
            is_blocked_resolver=MagicMock(side_effect=RuntimeError("boom")),
        )
        assert mgr.classify_announce("aa" * 16) == "blocked"

    def test_invalidate_forces_reload(self):
        db = _peer_sets_db()
        mgr = AnnounceManager(db)
        assert mgr.classify_announce("aa" * 16) == "background"
        db.misc.get_blocked_destinations.return_value = [
            {"destination_hash": "aa" * 16},
        ]
        mgr.invalidate_peer_sets()
        assert mgr.classify_announce("aa" * 16) == "blocked"


class TestDeferredJournal:
    def test_defer_does_not_write_db(self):
        db = _peer_sets_db()
        mgr = AnnounceManager(db)
        mgr.upsert_announce(
            None,
            _ident("11" * 16),
            b"\x22" * 16,
            "lxmf.delivery",
            b"data",
            None,
            defer=True,
        )
        db.announces.upsert_announce.assert_not_called()
        assert len(mgr._pending) == 1

    def test_defer_coalesces_same_destination(self):
        db = _peer_sets_db()
        mgr = AnnounceManager(db)
        for _ in range(5):
            mgr.upsert_announce(
                None,
                _ident("11" * 16),
                b"\x22" * 16,
                "lxmf.delivery",
                b"data",
                None,
                defer=True,
            )
        assert len(mgr._pending) == 1

    def test_journal_cap_drops_oldest(self):
        db = _peer_sets_db()
        mgr = AnnounceManager(db)
        first_dh = b"\x00" * 16
        mgr.upsert_announce(
            None,
            _ident("11" * 16),
            first_dh,
            "lxmf.delivery",
            b"d",
            None,
            defer=True,
        )
        for i in range(1, ANNOUNCE_JOURNAL_MAX_PENDING + 5):
            mgr.upsert_announce(
                None,
                _ident("11" * 16),
                i.to_bytes(16, "big"),
                "lxmf.delivery",
                b"d",
                None,
                defer=True,
            )
        assert len(mgr._pending) == ANNOUNCE_JOURNAL_MAX_PENDING
        assert first_dh.hex() not in mgr._pending

    def test_flush_pending_writes_rows(self, sqlite_db):
        mgr = AnnounceManager(sqlite_db)
        for i in range(3):
            dh = i.to_bytes(16, "big")
            mgr.upsert_announce(
                None,
                _ident(f"{i:032x}"),
                dh,
                "lxmf.delivery",
                b"payload",
                None,
                defer=True,
            )
        assert len(mgr._pending) == 3
        mgr.flush_pending()
        assert len(mgr._pending) == 0
        assert sqlite_db.announces.get_announce_count_by_aspect("lxmf.delivery") == 3

    def test_flush_pending_requeues_rows_on_failure(self, sqlite_db):
        mgr = AnnounceManager(sqlite_db)
        for i in range(3):
            mgr.upsert_announce(
                None,
                _ident(f"{i:032x}"),
                i.to_bytes(16, "big"),
                "lxmf.delivery",
                b"payload",
                None,
                defer=True,
            )
        assert len(mgr._pending) == 3
        with patch.object(
            sqlite_db.announces,
            "upsert_announce",
            side_effect=RuntimeError("commit failed"),
        ):
            mgr.flush_pending()
        # A failed transaction must not drop the journaled rows.
        assert len(mgr._pending) == 3
        assert sqlite_db.announces.get_announce_count_by_aspect("lxmf.delivery") == 0
        mgr.flush_pending()
        assert len(mgr._pending) == 0
        assert sqlite_db.announces.get_announce_count_by_aspect("lxmf.delivery") == 3

    def test_flush_pending_requeue_respects_cap(self, sqlite_db):
        mgr = AnnounceManager(sqlite_db)
        for i in range(ANNOUNCE_JOURNAL_MAX_PENDING):
            mgr.upsert_announce(
                None,
                _ident("11" * 16),
                i.to_bytes(16, "big"),
                "lxmf.delivery",
                b"d",
                None,
                defer=True,
            )
        first_dh = (0).to_bytes(16, "big").hex()
        new_dh = (b"\xff" * 16).hex()

        def _fail_and_enqueue(_data):
            # Simulate an announce arriving while the failed flush runs.
            with mgr._pending_lock:
                mgr._pending[new_dh] = {"destination_hash": new_dh}
            raise RuntimeError("commit failed")

        with patch.object(
            sqlite_db.announces,
            "upsert_announce",
            side_effect=_fail_and_enqueue,
        ):
            mgr.flush_pending()
        assert len(mgr._pending) == ANNOUNCE_JOURNAL_MAX_PENDING
        # The newest entry survives; the oldest requeued rows absorb the cap.
        assert new_dh in mgr._pending
        assert first_dh not in mgr._pending

    def test_flush_pending_empty_is_noop(self, sqlite_db):
        mgr = AnnounceManager(sqlite_db)
        mgr.flush_pending()

    def test_stop_flushes_pending(self, sqlite_db):
        mgr = AnnounceManager(sqlite_db)
        mgr.start()
        mgr.upsert_announce(
            None,
            _ident("33" * 16),
            b"\x44" * 16,
            "lxmf.delivery",
            b"d",
            None,
            defer=True,
        )
        mgr.stop()
        assert len(mgr._pending) == 0
        assert sqlite_db.announces.get_announce_count_by_aspect("lxmf.delivery") == 1
        assert mgr._flush_thread is None

    def test_flush_thread_writes_periodically(self, sqlite_db):
        import meshchatx.src.backend.announce_manager as am

        original = am.ANNOUNCE_JOURNAL_FLUSH_SECONDS
        am.ANNOUNCE_JOURNAL_FLUSH_SECONDS = 0.05
        try:
            mgr = AnnounceManager(sqlite_db)
            mgr.start()
            mgr.upsert_announce(
                None,
                _ident("55" * 16),
                b"\x66" * 16,
                "lxmf.delivery",
                b"d",
                None,
                defer=True,
            )
            deadline = threading.Event()
            assert deadline.wait(2.0) is False
            # Poll the DB until the flush thread commits.
            for _ in range(100):
                if (
                    sqlite_db.announces.get_announce_count_by_aspect(
                        "lxmf.delivery",
                    )
                    == 1
                ):
                    break
                deadline.wait(0.05)
            mgr.stop()
            assert (
                sqlite_db.announces.get_announce_count_by_aspect("lxmf.delivery") == 1
            )
        finally:
            am.ANNOUNCE_JOURNAL_FLUSH_SECONDS = original

    def test_flush_trims_per_aspect(self, sqlite_db):
        config = MagicMock()
        config.announce_max_stored_lxmf_delivery.get.return_value = 2
        config.announce_store_lxmf_delivery.get.return_value = True
        mgr = AnnounceManager(sqlite_db, config=config)
        for i in range(5):
            mgr.upsert_announce(
                None,
                _ident(f"{i:032x}"),
                i.to_bytes(16, "big"),
                "lxmf.delivery",
                b"d",
                None,
                defer=True,
            )
        mgr.flush_pending()
        assert sqlite_db.announces.get_announce_count_by_aspect("lxmf.delivery") == 2
