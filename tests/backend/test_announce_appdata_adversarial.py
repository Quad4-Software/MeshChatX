# SPDX-License-Identifier: 0BSD
"""Malformed announce app_data at the AnnounceManager boundary."""

import base64
from types import SimpleNamespace

import pytest

from meshchatx.src.backend.announce_manager import (
    ANNOUNCE_JOURNAL_MAX_PENDING,
    MAX_ANNOUNCE_APP_DATA_BYTES,
    AnnounceManager,
)


def _ident(h=b"\x01" * 64):
    return SimpleNamespace(
        hash=SimpleNamespace(hex=lambda: "ab" * 32), get_public_key=lambda: b"\x02" * 64
    )


def _stored(mgr, db, dest):
    return db.announces.get_announce_by_hash(dest)


class TestAppDataBoundary:
    @pytest.mark.parametrize(
        "size",
        [
            0,
            1,
            MAX_ANNOUNCE_APP_DATA_BYTES - 1,
            MAX_ANNOUNCE_APP_DATA_BYTES,
            MAX_ANNOUNCE_APP_DATA_BYTES + 1,
            65536,
        ],
    )
    def test_app_data_cap(self, db, size):
        mgr = AnnounceManager(db)
        dest = "cd" * 16
        mgr.upsert_announce(None, _ident(), dest, "lxmf.delivery", b"\x42" * size, None)
        row = _stored(mgr, db, dest)
        assert row is not None
        stored = row["app_data"]
        if size <= MAX_ANNOUNCE_APP_DATA_BYTES:
            assert stored == base64.b64encode(b"\x42" * size).decode()
        else:
            # Oversized payload must be dropped, never truncated-stored.
            assert stored is None

    @pytest.mark.parametrize(
        "bad", [{"a": 1}, "text", 123, ["x"], memoryview(b"mv" * 2000)]
    )
    def test_non_bytes_or_huge_memoryview_dropped(self, db, bad):
        mgr = AnnounceManager(db)
        dest = "ef" * 16
        mgr.upsert_announce(None, _ident(), dest, "lxmf.delivery", bad, None)
        row = _stored(mgr, db, dest)
        assert row is not None  # announce stored, payload dropped
        if isinstance(bad, memoryview) and len(bad) <= MAX_ANNOUNCE_APP_DATA_BYTES:
            assert row["app_data"] is not None
        else:
            assert row["app_data"] is None

    def test_pending_journal_cap_evicts_oldest(self, db):
        mgr = AnnounceManager(db)
        n = ANNOUNCE_JOURNAL_MAX_PENDING + 50
        for i in range(n):
            mgr.upsert_announce(
                None,
                _ident(),
                f"{i:032x}",
                "nomadnetwork.node",
                b"x",
                None,
                defer=True,
            )
        assert len(mgr._pending) == ANNOUNCE_JOURNAL_MAX_PENDING
        keys = list(mgr._pending)
        # Oldest 50 evicted. Dict order keeps newest at the tail.
        assert f"{0:032x}" not in mgr._pending
        assert keys[-1] == f"{n - 1:032x}"
        assert keys[0] == f"{50:032x}"
