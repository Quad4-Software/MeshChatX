# SPDX-License-Identifier: 0BSD

"""Chaos, corruption, and race coverage for crash recovery and async paths.

These tests poke the parts of the app where a failure inside the failure
handler, a mid-send disconnect, or two threads racing the same report could
turn one bug into a wedge or a flood.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest_asyncio

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.async_utils import (
    AsyncUtils as RealAsyncUtils,
)
from meshchatx.src.backend.async_utils import (
    call_soon_threadsafe_or_none,
)
from meshchatx.src.backend.recovery.crash_recovery import CrashRecovery

# ----------------------------------------------------------------------
# Crash recovery: chaos + races
# ----------------------------------------------------------------------


def _recovery(storage_dir=None):
    return CrashRecovery(
        storage_dir=storage_dir or os.devnull,
        public_dir=None,
        database_path=None,
        reticulum_config_dir=None,
    )


class TestCrashRecoveryChaos:
    def test_concurrent_thread_crashes_produce_distinct_reports(self, tmp_path):
        """Simultaneous crashes on several threads must serialize, not garble."""
        recovery = _recovery(str(tmp_path))
        barrier = threading.Barrier(4)
        errors = []

        def crash(kind):
            try:
                barrier.wait(timeout=5)
                try:
                    raise kind(f"boom-{kind.__name__}")
                except Exception:
                    recovery.handle_exception(*sys.exc_info(), exit_process=False)
            except Exception as e:
                errors.append(e)

        output = io.StringIO()
        original = sys.stderr
        sys.stderr = output
        try:
            threads = [
                threading.Thread(target=crash, args=(kind,), daemon=True)
                for kind in (ValueError, KeyError, OSError, TypeError)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)
        finally:
            sys.stderr = original

        assert not errors
        text = output.getvalue()
        # Four distinct signatures, so no suppression: four complete reports.
        assert text.count("APPLICATION CRASH DETECTED") == 4
        for kind in (ValueError, KeyError, OSError, TypeError):
            assert f"boom-{kind.__name__}" in text
        assert text.count("Recovery Suggestions:") == 4

    def test_crash_survives_db_write_failure(self, tmp_path):
        """A crash_history insert that raises must not kill the report."""
        recovery = _recovery(str(tmp_path))
        db = MagicMock()
        db.crash_history.insert_crash.side_effect = RuntimeError("db locked")
        db.crash_history.get_recent_crashes.return_value = []
        db.config.get.return_value = None
        recovery.set_database(db)

        output = io.StringIO()
        original = sys.stderr
        sys.stderr = output
        try:
            try:
                raise ValueError("crash while db writes fail")
            except ValueError:
                recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original

        text = output.getvalue()
        assert "APPLICATION CRASH DETECTED" in text
        assert "Recovery Suggestions:" in text

    def test_crash_survives_diagnosis_failure(self, tmp_path):
        """run_diagnosis raising (e.g. psutil gone) still renders the report."""
        recovery = _recovery(str(tmp_path))
        recovery.run_diagnosis = MagicMock(side_effect=RuntimeError("psutil gone"))

        output = io.StringIO()
        original = sys.stderr
        sys.stderr = output
        try:
            try:
                raise RuntimeError("mid-diagnosis failure")
            except RuntimeError:
                recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original

        text = output.getvalue()
        assert "APPLICATION CRASH DETECTED" in text
        assert "Failed to complete diagnosis" in text
        assert "Technical Traceback:" in text

    def test_crash_survives_unwritable_report_dir(self, tmp_path):
        """A storage dir that is a file (not writable) still reports to stderr."""
        blocker = tmp_path / "not_a_dir"
        blocker.write_text("x")
        recovery = _recovery(str(blocker))
        # _open_report_file must degrade to None instead of raising.
        assert recovery._open_report_file("sig") is None

        output = io.StringIO()
        original = sys.stderr
        sys.stderr = output
        try:
            try:
                raise ValueError("report file write will fail")
            except ValueError:
                recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original

        assert "APPLICATION CRASH DETECTED" in output.getvalue()

    def test_repeat_signature_hammering_stays_suppressed(self, tmp_path):
        """Many same-site crashes inside the window produce one full report."""
        recovery = _recovery(str(tmp_path))

        def boom():
            raise RuntimeError("identical crash")

        output = io.StringIO()
        original = sys.stderr
        sys.stderr = output
        try:
            for _ in range(8):
                try:
                    boom()
                except RuntimeError:
                    recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original

        text = output.getvalue()
        assert text.count("APPLICATION CRASH DETECTED") == 1
        assert text.count("repeat crash") == 7

    def test_nonblocking_report_does_not_stall_when_lock_held(self, tmp_path):
        """Loop/GC paths must not wait on a busy report lock."""
        recovery = _recovery(str(tmp_path))
        output = io.StringIO()
        original = sys.stderr
        sys.stderr = output
        try:
            recovery._report_lock.acquire()
            started = time.monotonic()
            try:
                raise ValueError("deferred")
            except ValueError:
                recovery.handle_exception(
                    *sys.exc_info(),
                    exit_process=False,
                    wait_for_report=False,
                )
            elapsed = time.monotonic() - started
        finally:
            recovery._report_lock.release()
            sys.stderr = original

        assert elapsed < 5
        assert "deferred" in output.getvalue()

    def test_signature_map_bounded_under_churn(self, tmp_path):
        """Distinct signatures must not grow _signature_last_report unboundedly."""
        recovery = _recovery(str(tmp_path))
        recovery._signature_last_report = {
            f"sig{i}": time.monotonic() for i in range(300)
        }
        recovery._is_repeat_signature("fresh-sig")
        assert len(recovery._signature_last_report) <= 300


class TestCrashHistoryCorruption:
    def test_garbage_symptoms_rows_do_not_break_counting(self, tmp_path):
        """Stored crash rows with unparseable symptoms are skipped."""
        recovery = _recovery(str(tmp_path))
        recovery.database = MagicMock()
        recovery.database.crash_history.get_recent_crashes.return_value = [
            {"symptoms": "not json"},
            {"symptoms": 42},
            {"symptoms": json.dumps({"_signature": "abc"})},
            {"symptoms": {"_signature": "abc"}},
        ]
        assert recovery._count_signature_occurrences("abc") == 2
        assert recovery._count_signature_occurrences("other") == 0

    def test_corrupt_learned_weights_fall_back_to_defaults(self, tmp_path):
        """Unparseable diagnostic_weights must not poison priors."""
        recovery = _recovery(str(tmp_path))
        recovery.database = MagicMock()
        recovery.database.config.get.return_value = "{not valid json"
        recovery._load_learned_priors()
        assert recovery._learned_priors is None
        assert recovery._get_prior("OOM") == 0.02


# ----------------------------------------------------------------------
# AsyncUtils: loop-edge races
# ----------------------------------------------------------------------


class TestAsyncUtilsLoopEdges:
    def test_call_soon_threadsafe_or_none_on_closed_loop(self):
        loop = asyncio.new_event_loop()
        loop.close()
        assert call_soon_threadsafe_or_none(loop, lambda: None) is False

    def test_call_soon_threadsafe_or_none_on_running_loop(self):
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, daemon=True)
        thread.start()
        try:
            ran = threading.Event()
            assert call_soon_threadsafe_or_none(loop, ran.set) is True
            assert ran.wait(timeout=5)
        finally:
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=5)
            loop.close()


# ----------------------------------------------------------------------
# websocket_broadcast: races and client failures
# ----------------------------------------------------------------------


class _FakeWs:
    """Plain object so attribute probes behave like a real ws client."""


def _bare_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.websocket_clients = []
    app.ws_seq_state = None
    app.ws_counters = None
    app._ws_coalesce = None
    app._websocket_broadcast_lock = asyncio.Lock()
    app._detach_active_session = MagicMock(return_value=False)
    return app


@pytest_asyncio.fixture
async def on_real_loop():
    """Point AsyncUtils.main_loop at the pytest loop so broadcasts run inline."""
    loop = asyncio.get_running_loop()
    old = RealAsyncUtils.main_loop
    RealAsyncUtils.main_loop = loop
    try:
        with patch("meshchatx.meshchat.AsyncUtils", RealAsyncUtils):
            yield loop
    finally:
        RealAsyncUtils.main_loop = old


async def test_broadcast_concurrent_sends_all_delivered(on_real_loop):
    """Concurrent broadcasts on the owning loop serialize through the lock."""
    app = _bare_app()
    received = []
    client = _FakeWs()

    async def send_str(data):
        await asyncio.sleep(0)
        received.append(json.loads(data))

    client.send_str = send_str
    app.websocket_clients = [client]

    await asyncio.gather(
        *[app.websocket_broadcast({"type": "chaos.event", "n": i}) for i in range(8)]
    )
    assert len(received) == 8


async def test_broadcast_dead_client_pruned_others_served(on_real_loop):
    """A failing client is dropped while healthy clients still receive."""
    app = _bare_app()
    good_recv = []
    good = _FakeWs()

    async def good_send(data):
        good_recv.append(data)

    good.send_str = good_send

    bad = _FakeWs()

    async def explode(data):
        raise ConnectionError("socket gone")

    bad.send_str = explode

    async def close(code=None):
        bad.closed = code

    bad.close = close

    app.websocket_clients = [bad, good]
    await app.websocket_broadcast(json.dumps({"type": "chaos.event"}))

    assert len(good_recv) == 1
    # The failing client must be removed from the client list.
    assert bad not in app.websocket_clients
    assert good in app.websocket_clients


async def test_broadcast_seq_stamps_in_send_order(on_real_loop):
    """Seq numbers observed by a client must be monotonic under concurrency."""
    from meshchatx.src.backend.websocket_runtime import BroadcastSeqState

    app = _bare_app()
    app.ws_seq_state = BroadcastSeqState()
    seen_seqs = []
    client = _FakeWs()

    async def send_str(data):
        await asyncio.sleep(0)
        seen_seqs.append(json.loads(data)["seq"])

    client.send_str = send_str
    app.websocket_clients = [client]

    await asyncio.gather(
        *[app.websocket_broadcast({"type": "chaos.seq", "n": i}) for i in range(10)]
    )
    assert seen_seqs == sorted(seen_seqs)
    assert len(set(seen_seqs)) == 10


async def test_broadcast_holds_under_lock_contention(on_real_loop):
    """A broadcast queued behind a held lock completes once released."""
    app = _bare_app()
    received = []
    client = _FakeWs()

    async def send_str(data):
        received.append(json.loads(data))

    client.send_str = send_str
    app.websocket_clients = [client]

    await app._websocket_broadcast_lock.acquire()
    task = asyncio.ensure_future(
        app.websocket_broadcast({"type": "chaos.deferred"}),
    )
    await asyncio.sleep(0.05)
    assert received == []
    app._websocket_broadcast_lock.release()
    await asyncio.wait_for(task, timeout=5)
    assert len(received) == 1


# ----------------------------------------------------------------------
# DatabaseProvider: concurrent config access
# ----------------------------------------------------------------------


def test_config_concurrent_set_get_race(db):
    """Threads hammering config.set/get on shared keys must not error."""
    errors = []
    barrier = threading.Barrier(6)

    def churn(i):
        try:
            barrier.wait(timeout=5)
            for n in range(25):
                key = f"chaos.key.{n % 4}"
                db.config.set(key, f"v{i}-{n}")
                db.config.get(key)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=churn, args=(i,), daemon=True) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors
    # Last-writer consistency: every read returns a value from a real write.
    for n in range(4):
        val = db.config.get(f"chaos.key.{n}")
        assert val is not None and val.startswith("v")


def test_crash_history_insert_under_concurrent_writers(db):
    """crash_history inserts racing other writers must not lose rows."""
    errors = []
    barrier = threading.Barrier(4)

    def writer(i):
        try:
            barrier.wait(timeout=5)
            for n in range(10):
                db.crash_history.insert_crash(
                    timestamp=time.time(),
                    error_type="RaceError",
                    error_message=f"w{i}-{n}",
                    diagnosed_cause="Unknown",
                    symptoms={"i": i},
                    probability=10,
                    entropy=0.0,
                    divergence=0.0,
                )
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer, args=(i,), daemon=True) for i in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors
    rows = db.crash_history.get_recent_crashes(limit=100)
    assert len(rows) == 40
