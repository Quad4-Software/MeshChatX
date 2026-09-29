"""Task scheduling system for LXMFy.

This module provides cron-style scheduling and background task management
for LXMFy bots.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Event, Thread

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A scheduled task with cron-style timing.

    Attributes:
        name (str): The name of the task.
        callback (Callable): The function to execute when the task runs.
        cron_expr (str): A cron-style expression defining when the task should run (min hour day month weekday).
        last_run (Optional[datetime]): The last time the task was run.
        enabled (bool): Whether the task is currently enabled.

    """

    name: str
    callback: Callable
    cron_expr: str
    last_run: datetime | None = None
    enabled: bool = True

    def should_run(self, current_time: datetime) -> bool:
        """Check if the task should run at the given time.

        Args:
            current_time (datetime): The current datetime.

        Returns:
            bool: True if the task should run, False otherwise.

        """
        if not self.enabled:
            return False

        if self.last_run and current_time - self.last_run < timedelta(minutes=1):
            return False

        return self._match_cron(current_time)

    def _match_cron(self, dt: datetime) -> bool:
        """Match the datetime against the cron expression.

        Args:
            dt (datetime): The datetime to match.

        Returns:
            bool: True if the datetime matches the cron expression, False otherwise.

        """
        parts = self.cron_expr.split()
        if len(parts) != 5:
            return False

        minute, hour, day, month, weekday = parts

        return (
            self._match_field(minute, dt.minute, 0, 59)
            and self._match_field(hour, dt.hour, 0, 23)
            and self._match_field(day, dt.day, 1, 31)
            and self._match_field(month, dt.month, 1, 12)
            and ScheduledTask._match_field(weekday, dt.weekday(), 0, 6)
        )

    @staticmethod
    def _match_field(pattern: str, value: int, min_val: int, max_val: int) -> bool:
        """Match a cron field pattern.

        Args:
            pattern (str): The cron field pattern to match.
            value (int): The value to check against the pattern.
            min_val (int): The minimum allowed value.
            max_val (int): The maximum allowed value.

        Returns:
            bool: True if the value matches the pattern, False otherwise.

        """
        if pattern == "*":
            return True

        parts = pattern.split(",")
        for part in parts:
            if "-" in part:
                start, end = map(int, part.split("-"))
                if min_val <= start <= value <= end <= max_val:
                    return True
            elif "/" in part:
                step = int(part.split("/")[1])
                if value % step == 0:
                    return True
            elif int(part) == value:
                return True

        return False


class TaskScheduler:
    """Manages scheduled tasks and background processes."""

    def __init__(self, bot):
        """Initialize the TaskScheduler.

        Args:
            bot: The bot instance.

        """
        self.bot = bot
        self.tasks: dict[str, ScheduledTask] = {}
        self.background_tasks: list[Thread] = []
        self.stop_event = Event()
        self.logger = logging.getLogger(__name__)

    def schedule(self, name: str, cron_expr: str):
        """Decorator to schedule a task.

        Args:
            name (str): The name of the task.
            cron_expr (str): The cron expression for the task.

        """

        def decorator(func):
            """Adds the task to the scheduler."""
            self.add_task(name, func, cron_expr)
            return func

        return decorator

    def add_task(self, name: str, callback: Callable, cron_expr: str):
        """Add a scheduled task.

        Args:
            name (str): The name of the task.
            callback (Callable): The function to execute when the task runs.
            cron_expr (str): A cron-style expression defining when the task should run.

        """
        self.tasks[name] = ScheduledTask(name, callback, cron_expr)

    def remove_task(self, name: str):
        """Remove a scheduled task.

        Args:
            name (str): The name of the task to remove.

        """
        self.tasks.pop(name, None)

    def start(self):
        """Start the scheduler."""
        self.stop_event.clear()
        scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        self.background_tasks.append(scheduler_thread)

    def stop(self):
        """Stop the scheduler."""
        self.stop_event.set()
        for task in self.background_tasks:
            task.join()
        self.background_tasks.clear()

    def _scheduler_loop(self):
        """Main scheduler loop.  Checks and runs tasks based on their cron expressions."""
        while not self.stop_event.is_set():
            current_time = datetime.now()

            for task in self.tasks.values():
                if task.should_run(current_time):
                    try:
                        task.callback()
                        task.last_run = current_time
                    except Exception as e:
                        self.logger.error(
                            "Error running task %s: %s",
                            task.name,
                            str(e),
                        )

            time.sleep(60 - datetime.now().second)
