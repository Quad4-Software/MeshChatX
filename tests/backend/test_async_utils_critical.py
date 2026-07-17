# SPDX-License-Identifier: 0BSD

"""Critical-path tests for AsyncUtils: cross-thread scheduling and memory caps."""

from __future__ import annotations

import asyncio
import threading
import time
import warnings

import pytest

from meshchatx.src.backend.async_utils import AsyncUtils


@pytest.fixture(autouse=True)
def _reset_async_utils():
    AsyncUtils.main_loop = None
    AsyncUtils._pending_futures.clear()
    AsyncUtils._pending_coroutines.clear()
    AsyncUtils._background_loop = None
    AsyncUtils._background_thread = None
    AsyncUtils._background_ready.clear()
    yield
    AsyncUtils.main_loop = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        AsyncUtils._pending_futures.clear()
        AsyncUtils._pending_coroutines.clear()
    if AsyncUtils._background_loop and AsyncUtils._background_loop.is_running():
        AsyncUtils._background_loop.call_soon_threadsafe(
            AsyncUtils._background_loop.stop,
        )
    AsyncUtils._background_loop = None
    AsyncUtils._background_thread = None
    AsyncUtils._background_ready.clear()


def test_ensure_background_loop_schedules_coroutines_before_web_startup():
    seen: list[bool] = []

    async def record():
        seen.append(True)

    AsyncUtils.ensure_background_loop()
    AsyncUtils.run_async(record())

    deadline = time.time() + 2.0
    while time.time() < deadline and not seen:
        time.sleep(0.05)

    assert seen == [True]


async def _noop():
    return None


def test_buffered_coroutines_capped_when_event_loop_not_running():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for _ in range(AsyncUtils._COROUTINES_MAX + 12):
            AsyncUtils.run_async(_noop())

    assert len(AsyncUtils._pending_coroutines) == AsyncUtils._COROUTINES_MAX


@pytest.mark.asyncio
async def test_set_main_loop_drains_buffered_coroutines():
    seen: list[bool] = []

    async def record():
        seen.append(True)

    AsyncUtils.main_loop = None

    queued = threading.Event()

    def schedule_from_worker():
        AsyncUtils.run_async(record())
        queued.set()

    threading.Thread(target=schedule_from_worker).start()
    assert queued.wait(timeout=2.0)
    assert len(AsyncUtils._pending_coroutines) == 1

    AsyncUtils.set_main_loop(asyncio.get_running_loop())
    assert AsyncUtils._pending_coroutines == []

    await asyncio.sleep(0.15)
    assert seen == [True]


@pytest.mark.asyncio
async def test_run_async_with_running_loop_executes_coroutine():
    outcomes: list[int] = []

    async def work():
        outcomes.append(7)

    AsyncUtils.set_main_loop(asyncio.get_running_loop())

    done = threading.Event()

    def schedule_from_worker():
        AsyncUtils.run_async(work())
        done.set()

    threading.Thread(target=schedule_from_worker).start()
    assert done.wait(timeout=2.0)
    await asyncio.sleep(0.15)
    assert outcomes == [7]


@pytest.mark.asyncio
async def test_pending_futures_list_sheds_completed_entries():
    AsyncUtils.set_main_loop(asyncio.get_running_loop())
    with AsyncUtils._futures_lock:
        AsyncUtils._pending_futures.clear()

    finished = threading.Event()

    def blast():
        for _ in range(AsyncUtils._FUTURES_SWEEP_THRESHOLD + 8):
            AsyncUtils.run_async(asyncio.sleep(0))
        finished.set()

    threading.Thread(target=blast).start()
    assert finished.wait(timeout=5.0)
    await asyncio.sleep(0.15)

    with AsyncUtils._futures_lock:
        still_pending = [f for f in AsyncUtils._pending_futures if not f.done()]
    assert len(still_pending) == 0
