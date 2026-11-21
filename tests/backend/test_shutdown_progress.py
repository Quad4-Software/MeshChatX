# SPDX-License-Identifier: 0BSD

"""Shutdown progress reporting, per-step timeouts, and the exit watchdog."""

from __future__ import annotations

import asyncio
import json
import threading
import time

import pytest

from meshchatx.src.backend.lifecycle import shutdown_progress as sp


@pytest.fixture(autouse=True)
def _reset_progress():
    sp.reset_for_tests()
    yield
    sp.reset_for_tests()


def _fake_clock():
    state = {"t": 0.0}

    def clock():
        return state["t"]

    def advance(seconds):
        state["t"] += seconds

    return clock, advance


def test_report_writes_steps_with_elapsed(tmp_path):
    clock, advance = _fake_clock()
    lines = []
    p = sp.ShutdownProgress(
        str(tmp_path / "shutdown-status.json"),
        clock=clock,
        printer=lines.append,
        deadline_s=12.0,
    )
    p.report("signal", "received signal 15")
    advance(1.5)
    p.report("databases", "checkpoint and close")

    payload = json.loads((tmp_path / "shutdown-status.json").read_text())
    assert payload["seq"] == 2
    assert payload["step"] == "databases"
    assert payload["detail"] == "checkpoint and close"
    assert payload["elapsed_ms"] == 1500
    assert payload["deadline_s"] == 12.0
    assert lines == [
        "[shutdown] signal: received signal 15",
        "[shutdown] databases: checkpoint and close",
    ]


def test_report_survives_missing_dir_and_bad_path(tmp_path):
    p = sp.ShutdownProgress(
        str(tmp_path / "sub" / "dir" / "s.json"), printer=lambda line: None
    )
    p.report("step")
    assert (
        json.loads((tmp_path / "sub" / "dir" / "s.json").read_text())["step"] == "step"
    )

    # An unwritable path must never break the shutdown sequence.
    p2 = sp.ShutdownProgress("/nonexistent-root/x/y/z.json", printer=lambda line: None)
    p2.report("step")


def test_env_var_overrides_status_path(monkeypatch, tmp_path):
    monkeypatch.setenv("MESHCHATX_SHUTDOWN_STATUS", str(tmp_path / "env.json"))
    p = sp.init_progress("/storage/that/is/ignored")
    assert p.path == str(tmp_path / "env.json")


@pytest.mark.asyncio
async def test_run_step_success_and_timeout(tmp_path):
    lines = []
    p = sp.ShutdownProgress(None, printer=lines.append)

    ran = threading.Event()
    await sp.run_step(p, "fast", ran.set, timeout=1.0)
    assert ran.is_set()

    def slow():
        time.sleep(5)

    await sp.run_step(p, "slow", slow, timeout=0.05)
    assert any("timed out" in line for line in lines)


@pytest.mark.asyncio
async def test_run_step_swallows_step_errors(tmp_path):
    lines = []
    p = sp.ShutdownProgress(None, printer=lines.append)

    def boom():
        raise RuntimeError("dead link")

    await sp.run_step(p, "network", boom, timeout=1.0)
    assert any("dead link" in line for line in lines)


@pytest.mark.asyncio
async def test_run_step_async_reports_timeout():
    lines = []
    p = sp.ShutdownProgress(None, printer=lines.append)

    async def never():
        await asyncio.sleep(60)

    await sp.run_step_async(p, "websockets", never, timeout=0.05)
    assert any("websockets" in line and "timed out" in line for line in lines)


def test_watchdog_fires_exit_at_deadline():
    sp.reset_for_tests()
    exited = []
    real_event = threading.Event()
    disarm = sp.arm_watchdog(
        0.05,
        exit_fn=exited.append,
        on_fire=lambda: real_event.set(),
    )
    assert real_event.wait(1.0)
    assert exited == [124]
    sp.reset_for_tests()
    disarm()


def test_watchdog_disarm_prevents_exit():
    sp.reset_for_tests()
    fired = threading.Event()
    exited = []
    disarm = sp.arm_watchdog(0.2, exit_fn=exited.append, on_fire=fired.set)
    disarm()
    assert not fired.wait(0.5)
    assert exited == []


def test_watchdog_second_arm_is_noop():
    sp.reset_for_tests()
    first = threading.Event()
    second = threading.Event()
    exited = []
    d1 = sp.arm_watchdog(0.05, exit_fn=exited.append, on_fire=first.set)
    d2 = sp.arm_watchdog(0.05, exit_fn=exited.append, on_fire=second.set)
    assert first.wait(1.0)
    assert not second.is_set()
    sp.reset_for_tests()
    d1()
    d2()
