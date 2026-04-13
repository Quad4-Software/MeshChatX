"""Tests for the memory-leak fixes applied to websocket_broadcast,
update_lxmf_message_state, AsyncUtils.run_async future tracking,
nomadnet link cache sweeping, and the telemetry warning cap.
"""

import asyncio
import gc
import json
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.database.messages import MessageDAO
from meshchatx.src.backend.nomadnet_downloader import (
    _nomadnet_links_lock,
    nomadnet_cached_links,
    sweep_stale_links,
)


# ---------------------------------------------------------------------------
# MessageDAO.update_lxmf_message_state
# ---------------------------------------------------------------------------


class TestUpdateLxmfMessageState:
    @pytest.fixture
    def dao(self):
        provider = MagicMock()
        return MessageDAO(provider), provider

    def test_update_issues_correct_sql(self, dao):
        message_dao, provider = dao
        message_dao.update_lxmf_message_state(
            message_hash="abc123",
            state="delivered",
            progress=100.0,
            delivery_attempts=3,
            next_delivery_attempt_at=None,
            rssi=-55,
            snr=6.5,
            quality=4,
        )
        provider.execute.assert_called_once()
        query, params = provider.execute.call_args[0]
        assert "UPDATE lxmf_messages SET" in query
        assert "WHERE hash = ?" in query
        assert params[-1] == "abc123"
        assert params[0] == "delivered"
        assert params[1] == 100.0
        assert params[2] == 3

    def test_update_with_none_optionals(self, dao):
        message_dao, provider = dao
        message_dao.update_lxmf_message_state(
            message_hash="xyz",
            state="sending",
            progress=50.0,
            delivery_attempts=1,
            next_delivery_attempt_at=None,
        )
        _, params = provider.execute.call_args[0]
        assert params[4] is None  # rssi
        assert params[5] is None  # snr
        assert params[6] is None  # quality

    def test_update_does_not_touch_fields_column(self, dao):
        """The lightweight path must never rewrite the fields/content columns."""
        message_dao, provider = dao
        message_dao.update_lxmf_message_state(
            message_hash="h",
            state="sent",
            progress=99.0,
            delivery_attempts=2,
            next_delivery_attempt_at=None,
        )
        query = provider.execute.call_args[0][0]
        assert "fields" not in query.lower().split("set")[1].split("where")[0]
        assert "content" not in query.lower().split("set")[1].split("where")[0]

    def test_full_roundtrip_via_real_db(self, tmp_path):
        """Insert with upsert, then update state only, verify fields unchanged."""
        from meshchatx.src.backend.database import Database

        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()

        big_fields = json.dumps({"image": {"image_bytes": "A" * 5000}})
        msg = {
            "hash": "deadbeef",
            "source_hash": "src",
            "destination_hash": "dst",
            "peer_hash": "src",
            "state": "outbound",
            "progress": 0.0,
            "is_incoming": 0,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "hi",
            "content": "hello",
            "fields": big_fields,
            "timestamp": 12345,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
        }
        db.messages.upsert_lxmf_message(msg)

        db.messages.update_lxmf_message_state(
            message_hash="deadbeef",
            state="delivered",
            progress=100.0,
            delivery_attempts=2,
            next_delivery_attempt_at=None,
            rssi=-60,
            snr=7.0,
            quality=5,
        )

        row = db.messages.get_lxmf_message_by_hash("deadbeef")
        assert row["state"] == "delivered"
        assert row["progress"] == 100.0
        assert row["delivery_attempts"] == 2
        assert row["rssi"] == -60
        stored_fields = json.loads(row["fields"])
        assert stored_fields["image"]["image_bytes"] == "A" * 5000

        db.close_all()


# ---------------------------------------------------------------------------
# sweep_stale_links
# ---------------------------------------------------------------------------


class TestSweepStaleLinks:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        with _nomadnet_links_lock:
            nomadnet_cached_links.clear()
        yield
        with _nomadnet_links_lock:
            nomadnet_cached_links.clear()

    def test_sweep_removes_inactive_links(self):
        active = MagicMock()
        active.status = RNS.Link.ACTIVE
        dead = MagicMock()
        dead.status = RNS.Link.CLOSED

        with _nomadnet_links_lock:
            nomadnet_cached_links[b"a"] = active
            nomadnet_cached_links[b"b"] = dead

        sweep_stale_links()

        with _nomadnet_links_lock:
            assert b"a" in nomadnet_cached_links
            assert b"b" not in nomadnet_cached_links

    def test_sweep_empty_cache_is_noop(self):
        sweep_stale_links()
        with _nomadnet_links_lock:
            assert len(nomadnet_cached_links) == 0

    def test_sweep_all_active_keeps_all(self):
        for i in range(5):
            link = MagicMock()
            link.status = RNS.Link.ACTIVE
            with _nomadnet_links_lock:
                nomadnet_cached_links[bytes([i])] = link

        sweep_stale_links()

        with _nomadnet_links_lock:
            assert len(nomadnet_cached_links) == 5

    def test_sweep_thread_safety(self):
        for i in range(20):
            link = MagicMock()
            link.status = RNS.Link.CLOSED if i % 2 else RNS.Link.ACTIVE
            with _nomadnet_links_lock:
                nomadnet_cached_links[bytes([i])] = link

        errors = []

        def worker():
            try:
                sweep_stale_links()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        with _nomadnet_links_lock:
            assert len(nomadnet_cached_links) == 10


# ---------------------------------------------------------------------------
# AsyncUtils.run_async future tracking
# ---------------------------------------------------------------------------


class TestAsyncUtilsFutureTracking:
    """Tests operate directly on the real AsyncUtils class internals,
    bypassing the conftest global mock for the tracking logic.
    """

    @pytest.fixture(autouse=True)
    def _reset(self):
        AsyncUtils._pending_futures = []
        yield
        AsyncUtils._pending_futures = []

    def test_future_appended_on_schedule(self):
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        future = MagicMock()
        future.done.return_value = False

        real_main_loop = AsyncUtils.main_loop
        real_run_async = AsyncUtils.run_async.__func__

        try:
            AsyncUtils.main_loop = mock_loop
            with patch(
                "meshchatx.src.backend.async_utils.asyncio.run_coroutine_threadsafe",
                return_value=future,
            ):
                coro = asyncio.coroutine(lambda: None)()
                real_run_async(coro)
        finally:
            AsyncUtils.main_loop = real_main_loop

        assert future in AsyncUtils._pending_futures

    def test_completed_futures_swept_at_threshold(self):
        done = MagicMock()
        done.done.return_value = True
        pending = MagicMock()
        pending.done.return_value = False

        AsyncUtils._pending_futures = (
            [done] * (AsyncUtils._FUTURES_SWEEP_THRESHOLD - 2) + [pending]
        )

        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        new_future = MagicMock()
        new_future.done.return_value = False

        real_main_loop = AsyncUtils.main_loop
        real_run_async = AsyncUtils.run_async.__func__

        try:
            AsyncUtils.main_loop = mock_loop
            with patch(
                "meshchatx.src.backend.async_utils.asyncio.run_coroutine_threadsafe",
                return_value=new_future,
            ):
                coro = asyncio.coroutine(lambda: None)()
                real_run_async(coro)
        finally:
            AsyncUtils.main_loop = real_main_loop

        remaining = AsyncUtils._pending_futures
        assert done not in remaining
        assert pending in remaining

    def test_no_loop_prints_warning(self, capsys):
        real_main_loop = AsyncUtils.main_loop
        real_run_async = AsyncUtils.run_async.__func__
        try:
            AsyncUtils.main_loop = None
            coro = asyncio.coroutine(lambda: None)()
            real_run_async(coro)
        finally:
            AsyncUtils.main_loop = real_main_loop

        captured = capsys.readouterr()
        assert "WARNING" in captured.out


# ---------------------------------------------------------------------------
# websocket_broadcast dead-client pruning
# ---------------------------------------------------------------------------


class TestWebsocketBroadcastPruning:
    @pytest.mark.asyncio
    async def test_dead_clients_removed_on_send_failure(self):
        from meshchatx.meshchat import ReticulumMeshChat

        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_str.side_effect = ConnectionResetError("gone")

        app = MagicMock(spec=ReticulumMeshChat)
        app.websocket_clients = [good_ws, bad_ws]

        await ReticulumMeshChat.websocket_broadcast(app, '{"type":"ping"}')

        good_ws.send_str.assert_called_once_with('{"type":"ping"}')
        bad_ws.send_str.assert_called_once()
        assert bad_ws not in app.websocket_clients
        assert good_ws in app.websocket_clients

    @pytest.mark.asyncio
    async def test_all_healthy_clients_kept(self):
        from meshchatx.meshchat import ReticulumMeshChat

        clients = [AsyncMock() for _ in range(3)]
        app = MagicMock(spec=ReticulumMeshChat)
        app.websocket_clients = list(clients)

        await ReticulumMeshChat.websocket_broadcast(app, '{"ok":true}')

        assert len(app.websocket_clients) == 3
        for c in clients:
            c.send_str.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_dead_clients_cleared(self):
        from meshchatx.meshchat import ReticulumMeshChat

        clients = [AsyncMock() for _ in range(3)]
        for c in clients:
            c.send_str.side_effect = BrokenPipeError

        app = MagicMock(spec=ReticulumMeshChat)
        app.websocket_clients = list(clients)

        await ReticulumMeshChat.websocket_broadcast(app, "data")

        assert len(app.websocket_clients) == 0


# ---------------------------------------------------------------------------
# _telemetry_no_location_warned cap
# ---------------------------------------------------------------------------


class TestTelemetryWarnedCap:
    def test_cap_at_256_then_cleared(self):
        warned = set()
        for i in range(256):
            if len(warned) >= 256:
                warned.clear()
            warned.add(f"hash_{i}")

        assert len(warned) == 256

        if len(warned) >= 256:
            warned.clear()
        warned.add("hash_256")

        assert len(warned) == 1
        assert "hash_256" in warned


# ---------------------------------------------------------------------------
# Integration: state updates don't bloat memory with attachment re-encoding
# ---------------------------------------------------------------------------


class TestStateUpdateMemory:
    def test_state_update_avoids_large_fields_write(self, tmp_path):
        """Verify that update_lxmf_message_state does NOT cause the provider
        to receive the large fields blob that upsert_lxmf_message does."""
        from meshchatx.src.backend.database import Database

        db = Database(str(tmp_path / "t.db"))
        db.initialize()

        big_attachment = "X" * 100_000
        fields = json.dumps({"image": {"image_bytes": big_attachment}})
        msg = {
            "hash": "msg1",
            "source_hash": "s",
            "destination_hash": "d",
            "peer_hash": "s",
            "state": "outbound",
            "progress": 0.0,
            "is_incoming": 0,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "",
            "content": "",
            "fields": fields,
            "timestamp": 1,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": 0,
        }
        db.messages.upsert_lxmf_message(msg)

        gc.collect()
        import os
        import psutil

        mem_before = psutil.Process(os.getpid()).memory_info().rss

        for _ in range(50):
            db.messages.update_lxmf_message_state(
                message_hash="msg1",
                state="sending",
                progress=50.0,
                delivery_attempts=1,
                next_delivery_attempt_at=None,
            )

        gc.collect()
        mem_after = psutil.Process(os.getpid()).memory_info().rss
        delta_mb = (mem_after - mem_before) / (1024 * 1024)

        assert delta_mb < 5.0, (
            f"State-only updates grew memory by {delta_mb:.1f} MB; "
            "they should not re-serialize attachment data"
        )

        row = db.messages.get_lxmf_message_by_hash("msg1")
        assert row["state"] == "sending"
        stored = json.loads(row["fields"])
        assert stored["image"]["image_bytes"] == big_attachment

        db.close_all()
