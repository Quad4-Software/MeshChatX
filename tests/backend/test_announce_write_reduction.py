# SPDX-License-Identifier: 0BSD
"""Write-reduction guarantees for the immediate (priority) announce path.

Two mechanisms, both behavior-preserving:

1. Byte-identical re-announces younger than 60s skip the rewrite; the
   deferred announce_count increments fold into the next real write so
   the user-visible counter stays exact.
2. Per-aspect retention trims run at most once per 60s (monotonic)
   instead of after every immediate upsert.
"""

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


@pytest.fixture
def sqlite_db():
    db, path = _new_db()
    yield db, path
    _cleanup(db, path)


def _config(max_stored=None):
    config = MagicMock()
    attr = MagicMock()
    attr.get.return_value = max_stored
    config.announce_max_stored_lxmf_delivery = attr
    return config


def _counting_dao(db):
    real_upsert = db.announces.upsert_announce
    real_trim = db.announces.trim_announces_for_aspect
    calls = {"upserts": 0, "trims": 0}

    def counting_upsert(*args, **kwargs):
        calls["upserts"] += 1
        return real_upsert(*args, **kwargs)

    def counting_trim(*args, **kwargs):
        calls["trims"] += 1
        return real_trim(*args, **kwargs)

    db.announces.upsert_announce = counting_upsert
    db.announces.trim_announces_for_aspect = counting_trim
    return calls


def _announce(mgr, dest_hex, aspect="lxmf.delivery", app_data=b"payload", ret=None):
    return mgr.upsert_announce(
        ret or MagicMock(),
        _FakeIdentity("e" * 32),
        bytes.fromhex(dest_hex),
        aspect,
        app_data,
        None,
    )


def _age_stored_row(db, dest_hex, seconds):
    db.provider.execute(
        "UPDATE announces SET updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now', ?) "
        "WHERE destination_hash = ?",
        (f"-{seconds} seconds", dest_hex),
    )


# ---------------------------------------------------------------------------
# Skip of byte-identical re-announces
# ---------------------------------------------------------------------------


def test_first_announce_always_writes(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config())
    _announce(mgr, "f" * 32)
    assert calls["upserts"] == 1


def test_identical_reannounce_within_window_skips_write(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    _announce(mgr, dest)
    _announce(mgr, dest)
    _announce(mgr, dest)
    assert calls["upserts"] == 1
    # The two skipped increments are deferred in memory.
    assert mgr._pending_announce_counts[dest] == 2


def test_identical_reannounce_after_window_writes(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    _announce(mgr, dest)
    _announce(mgr, dest)
    assert calls["upserts"] == 1
    _age_stored_row(db, dest, 120)
    _announce(mgr, dest)
    assert calls["upserts"] == 2


def test_changed_app_data_writes_within_window(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    _announce(mgr, dest, app_data=b"v1")
    _announce(mgr, dest, app_data=b"v2")
    assert calls["upserts"] == 2


def test_changed_rssi_writes_within_window(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    ret = MagicMock()
    ret.get_packet_rssi.return_value = -50
    ret.get_packet_snr.return_value = None
    ret.get_packet_q.return_value = None
    packet = b"packet_hash"

    mgr.upsert_announce(
        ret,
        _FakeIdentity("e" * 32),
        bytes.fromhex(dest),
        "lxmf.delivery",
        b"payload",
        packet,
    )
    ret.get_packet_rssi.return_value = -80
    mgr.upsert_announce(
        ret,
        _FakeIdentity("e" * 32),
        bytes.fromhex(dest),
        "lxmf.delivery",
        b"payload",
        packet,
    )
    assert calls["upserts"] == 2


def test_missing_app_data_matches_coalesce_semantics(sqlite_db):
    """Re-announce without app_data is skippable under COALESCE semantics.

    The write would not change the stored blob, so skipping it loses
    nothing.
    """
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    _announce(mgr, dest, app_data=b"payload")
    _announce(mgr, dest, app_data=None)
    assert calls["upserts"] == 1
    row = db.announces.get_announce_by_hash(dest)
    assert row["app_data"] is not None


def test_announce_count_reconciled_on_next_write(sqlite_db):
    """Skipped increments fold into the next real write.

    The final count is exactly what unconditional writes would have
    produced.
    """
    db, _path = sqlite_db
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    _announce(mgr, dest)  # write, count 1
    _announce(mgr, dest)  # skip
    _announce(mgr, dest)  # skip
    row = db.announces.get_announce_by_hash(dest)
    assert row["announce_count"] == 1

    _age_stored_row(db, dest, 120)
    _announce(mgr, dest)  # window expired: write with folded increments
    row = db.announces.get_announce_by_hash(dest)
    assert row["announce_count"] == 4
    assert dest not in mgr._pending_announce_counts


def test_deferred_counts_survive_failed_write(sqlite_db):
    db, _path = sqlite_db
    mgr = AnnounceManager(db, _config())
    dest = "f" * 32
    _announce(mgr, dest)
    _announce(mgr, dest)  # skip, pending = 1
    _age_stored_row(db, dest, 120)

    real = db.announces.upsert_announce

    def exploding(*args, **kwargs):
        raise RuntimeError("disk full")

    db.announces.upsert_announce = exploding
    with pytest.raises(RuntimeError, match="disk full"):
        _announce(mgr, dest)
    db.announces.upsert_announce = real
    assert mgr._pending_announce_counts[dest] == 1

    _announce(mgr, dest)  # retry folds the restored increment
    row = db.announces.get_announce_by_hash(dest)
    # initial write (1) + skipped duplicate (1) + retry write (1). The
    # failed attempt's own increment is lost with its write, exactly as
    # a failed upsert loses it in the unbatched implementation.
    assert row["announce_count"] == 3


# ---------------------------------------------------------------------------
# Trim cadence
# ---------------------------------------------------------------------------


def test_trim_runs_on_first_immediate_upsert(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config(max_stored=5))
    _announce(mgr, "f" * 32)
    assert calls["trims"] == 1


def test_trim_gated_within_interval(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config(max_stored=5))
    for i in range(10):
        _announce(mgr, f"{i:032x}")
    assert calls["trims"] == 1
    # Rows may sit over cap inside the window; the cap is a retention
    # policy enforced at the next due trim, not a per-write invariant.
    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 10


def test_trim_runs_again_after_interval(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    mgr = AnnounceManager(db, _config(max_stored=5))
    for i in range(10):
        _announce(mgr, f"{i:032x}")
    assert calls["trims"] == 1

    # Simulate the interval elapsing (monotonic clock).
    mgr._last_trim_at["lxmf.delivery"] -= 61
    _announce(mgr, "aa" * 16)
    assert calls["trims"] == 2
    assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 5


def test_trim_cadence_is_per_aspect(sqlite_db):
    db, _path = sqlite_db
    calls = _counting_dao(db)
    config = _config(max_stored=5)
    node_attr = MagicMock()
    node_attr.get.return_value = 5
    config.announce_max_stored_nomadnetwork_node = node_attr
    mgr = AnnounceManager(db, config)
    _announce(mgr, "f" * 32, aspect="lxmf.delivery")
    _announce(mgr, "e" * 32, aspect="nomadnetwork.node")
    assert calls["trims"] == 2
