"""Tests for the cron task scheduler."""

import time
from datetime import datetime

from lxmfy.scheduler import ScheduledTask, TaskScheduler


def test_match_field_step_zero_does_not_raise():
    """A zero step must not crash the matcher."""
    task = ScheduledTask("t", lambda: None, "*/0 * * * *")
    assert task.should_run(datetime(2026, 1, 1, 0, 0)) is False


def test_match_field_step():
    task = ScheduledTask("t", lambda: None, "*/15 * * * *")
    assert task._match_field("*/15", 30, 0, 59) is True
    assert task._match_field("*/15", 31, 0, 59) is False


def test_match_field_malformed_parts():
    """Malformed field parts are ignored instead of raising."""
    task = ScheduledTask("t", lambda: None, "x * * * *")
    assert task._match_field("x", 5, 0, 59) is False
    assert task._match_field("*/abc", 5, 0, 59) is False
    assert task._match_field("a-b", 5, 0, 59) is False
    assert task._match_field("5", 5, 0, 59) is True
    assert task._match_field("1-10", 5, 0, 59) is True


def test_scheduler_loop_survives_bad_task(monkeypatch):
    """A task that raises in should_run must not kill the loop."""
    scheduler = TaskScheduler(bot=None)
    ran = []

    class BadTask(ScheduledTask):
        def should_run(self, current_time):
            raise ZeroDivisionError("boom")

    scheduler.tasks["bad"] = BadTask("bad", lambda: None, "*/0 * * * *")
    scheduler.tasks["good"] = ScheduledTask(
        "good",
        lambda: ran.append(1),
        "* * * * *",
    )

    def fast_wait(_timeout):
        scheduler.stop_event.set()
        return True

    monkeypatch.setattr(scheduler.stop_event, "wait", fast_wait)

    scheduler.start()
    for thread in scheduler.background_tasks:
        thread.join(2)
    assert ran == [1]


def test_scheduler_stop_does_not_block():
    """stop() must return promptly even mid-cycle."""
    scheduler = TaskScheduler(bot=None)
    scheduler.tasks["noop"] = ScheduledTask("noop", lambda: None, "* * * * *")
    scheduler.start()
    start = time.monotonic()
    scheduler.stop()
    assert time.monotonic() - start < 5
