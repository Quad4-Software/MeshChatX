# SPDX-License-Identifier: 0BSD

"""Collection-size oracles for in-process caches that must stay bounded."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.auto_resend_guard import (
    MAX_AUTO_RESEND_LOCKS,
    AutoResendCoordinator,
)
from meshchatx.src.backend.map_manager import MAX_EXPORT_RECORDS, MapManager
from meshchatx.src.backend.map_overlay_manager import (
    MAX_FINISHED_JOBS,
    MapOverlayManager,
)
from meshchatx.src.backend.memory_pressure import (
    ANNOUNCE_RATE_HARD_CAP,
    MemoryPressureManager,
    prune_announce_timestamps,
    prune_time_windowed_floats,
)
from meshchatx.src.backend.page_node import MAX_UNIQUE_REMOTE_HASHES, PageNode
from meshchatx.src.backend.rncp_handler import MAX_RETAINED_TRANSFERS, RNCPHandler


def test_announce_timestamps_drop_older_than_window():
    now = 10_000.0
    stamps = [now - 4000, now - 10, now]
    out = prune_time_windowed_floats(stamps, now=now, window_s=3600, hard_cap=50_000)
    assert out == [now - 10, now]


def test_announce_timestamps_hard_cap_inside_window():
    now = 1_000_000.0
    stamps = []
    for i in range(ANNOUNCE_RATE_HARD_CAP + 750):
        ts = now + (i * 0.001)
        stamps.append(ts)
        stamps = prune_announce_timestamps(stamps, now=ts)
    assert len(stamps) <= ANNOUNCE_RATE_HARD_CAP
    assert stamps[-1] >= stamps[0]


@settings(deadline=None, max_examples=40)
@given(
    stamps=st.lists(
        st.floats(
            min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False
        ),
        max_size=80,
    ),
    now=st.floats(
        min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False
    ),
    window_s=st.floats(
        min_value=1, max_value=10_000, allow_nan=False, allow_infinity=False
    ),
    hard_cap=st.integers(min_value=0, max_value=40),
)
def test_prune_time_windowed_floats_oracle(stamps, now, window_s, hard_cap):
    expected = [t for t in stamps if t >= now - window_s]
    if hard_cap and len(expected) > hard_cap:
        expected = expected[-hard_cap:]
    actual = prune_time_windowed_floats(
        list(stamps),
        now=now,
        window_s=window_s,
        hard_cap=hard_cap,
    )
    assert actual == expected
    assert len(actual) <= hard_cap if hard_cap else True


def test_auto_resend_locks_capped_for_unique_destinations():
    coord = AutoResendCoordinator()
    for i in range(MAX_AUTO_RESEND_LOCKS + 80):
        coord.lock_for("id1", f"{i:032x}")
    assert len(coord._locks) <= MAX_AUTO_RESEND_LOCKS


@pytest.mark.asyncio
async def test_auto_resend_held_lock_survives_eviction():
    coord = AutoResendCoordinator()
    held_dest = "aa" * 16
    lock = coord.lock_for("id1", held_dest)
    await lock.acquire()
    try:
        for i in range(MAX_AUTO_RESEND_LOCKS + 20):
            coord.lock_for("id1", f"{i:032x}")
        assert coord.lock_for("id1", held_dest) is lock
        assert lock.locked()
    finally:
        lock.release()


def test_auto_resend_drop_identity_removes_unlocked_locks():
    coord = AutoResendCoordinator()
    ident = "bb" * 16
    other = "cc" * 16
    coord.lock_for(ident, "11" * 16)
    coord.lock_for(other, "22" * 16)
    dropped = coord.drop_identity(ident)
    assert dropped == 1
    assert all(not key.startswith(ident + ":") for key in coord._locks)
    assert f"{other}:{'22' * 16}" in coord._locks


def test_rncp_drops_resource_and_caps_terminal_transfers():
    handler = RNCPHandler(MagicMock(), MagicMock(), "/tmp")
    blob = MagicMock()
    for i in range(MAX_RETAINED_TRANSFERS + 12):
        tid = f"{i:032x}"
        handler.active_transfers[tid] = {
            "resource": blob,
            "status": "completed",
            "started_at": float(i),
        }
        handler._on_transfer_terminal(tid)
    assert len(handler.active_transfers) <= MAX_RETAINED_TRANSFERS
    assert all("resource" not in entry for entry in handler.active_transfers.values())
    newest = max(handler.active_transfers, key=lambda tid: int(tid, 16))
    assert newest == f"{MAX_RETAINED_TRANSFERS + 11:032x}"


def test_page_node_unique_remote_hashes_capped():
    node = PageNode(
        node_id="n1",
        name="n1",
        base_dir="/tmp/page-node-mem",
        identity=MagicMock(),
        announce_enabled=False,
    )
    for i in range(MAX_UNIQUE_REMOTE_HASHES + 25):
        remote = MagicMock()
        remote.hash = i.to_bytes(16, "big")
        node._note_remote_identity(remote)
    assert len(node._unique_remote_hashes) == MAX_UNIQUE_REMOTE_HASHES


def test_map_overlay_finished_jobs_capped_and_cleanup_clears_locks():
    manager = MapOverlayManager.__new__(MapOverlayManager)
    manager._jobs = {}
    manager._active_fetchers = {}
    manager._source_locks = {1: object(), 2: object()}
    manager._scheduler_task = None
    manager._stopped = False
    for i in range(MAX_FINISHED_JOBS + 9):
        manager._jobs[f"job-{i}"] = {
            "job_id": f"job-{i}",
            "status": "success",
            "created_at": f"2026-01-01T00:00:{i:02d}",
        }
    dropped = manager.prune_finished_jobs()
    assert dropped == 9
    assert len(manager._jobs) == MAX_FINISHED_JOBS
    manager.stop_scheduler = lambda: None
    manager.overlay_root = lambda: "/tmp/missing-overlay-root"
    manager.cleanup()
    assert manager._jobs == {}
    assert manager._source_locks == {}


def test_map_export_records_capped():
    mm = MapManager(MagicMock(), "/tmp")
    for i in range(MAX_EXPORT_RECORDS + 5):
        mm._export_progress[f"e{i}"] = {
            "status": "completed",
            "start_time": float(i),
        }
    dropped = mm.prune_export_records()
    assert dropped == 5
    assert len(mm._export_progress) == MAX_EXPORT_RECORDS
    assert "e0" not in mm._export_progress
    assert f"e{MAX_EXPORT_RECORDS + 4}" in mm._export_progress


def test_identity_evict_drops_metrics_and_resend_locks():
    ident = "aa" * 16
    coord = AutoResendCoordinator()
    coord.lock_for(ident, "dd" * 16)
    app = SimpleNamespace(
        contexts={},
        _propagation_sync_metrics={ident: {"attempts": 3}},
        _auto_resend_coordinator=coord,
    )
    ReticulumMeshChat._evict_cached_identity_context(app, ident)
    assert ident not in app._propagation_sync_metrics
    assert coord._locks == {}


def test_periodic_cleanup_prunes_announce_timestamp_list():
    now = time.time()
    app = SimpleNamespace(
        announce_timestamps=[now - 8000, now - 10, now],
        _lxmf_incoming_timestamps=[now - 9000, now],
        reticulum=None,
        rnpath_handler=None,
        current_context=None,
        _auto_resend_coordinator=AutoResendCoordinator(),
    )
    manager = MemoryPressureManager(app=app)
    stats = manager.run_periodic_cleanup()
    assert app.announce_timestamps == [now - 10, now]
    assert app._lxmf_incoming_timestamps == [now]
    assert stats["announce_timestamps"] == 1
    assert stats["lxmf_incoming_timestamps"] == 1
