"""Reminder bot with SQLite storage."""

import re
import time
from datetime import datetime, timedelta

from lxmfy import LXMFBot


class ReminderBot:
    """A bot that reminds users of tasks at specified times."""

    def __init__(self, test_mode=False):
        """Initializes the ReminderBot, sets up the bot instance,
        configures commands, and sets up the reminder check loop.
        """
        self.bot = LXMFBot(
            name="Reminder Bot",
            announce=600,
            command_prefix="/",
            storage_type="sqlite",
            storage_path="data/reminders.db",
            test_mode=test_mode,
        )
        self.setup_commands()
        self.bot.scheduler.add_task(
            "check_reminders",
            self._check_reminders,
            "*/1 * * * *",  # Run every minute
        )

    def setup_commands(self):
        """Sets up the bot's commands, specifically the 'remind' and 'list' commands."""

        @self.bot.command(name="remind", description="Set a reminder")
        def remind(ctx):
            """Sets a reminder for the user.

            Args:
                ctx: The command context containing the sender and message.

            """
            if not ctx.args or len(ctx.args) < 2:
                ctx.reply(
                    "Usage: /remind <time> <message>\nExample: /remind 1h30m Buy groceries",
                )
                return

            time_str = ctx.args[0].lower()
            message = " ".join(ctx.args[1:])

            total_minutes = 0
            time_parts = re.findall(r"(\d+)([dhm])", time_str)

            for value, unit in time_parts:
                if unit == "d":
                    total_minutes += int(value) * 24 * 60
                elif unit == "h":
                    total_minutes += int(value) * 60
                elif unit == "m":
                    total_minutes += int(value)

            if total_minutes == 0:
                ctx.reply(
                    "Invalid time format. Use combinations of d (days), h (hours), m (minutes)",
                )
                return

            remind_time = datetime.now() + timedelta(minutes=total_minutes)

            reminder = {
                "user": ctx.sender,
                "message": message,
                "time": remind_time.timestamp(),
                "created": time.time(),
            }

            reminders = self.bot.storage.get("reminders", [])
            reminders.append(reminder)
            self.bot.storage.set("reminders", reminders)

            ctx.reply(
                f"I'll remind you about '{message}' at {remind_time.strftime('%Y-%m-%d %H:%M:%S')}",
            )

        @self.bot.command(name="list", description="List your reminders")
        def list_reminders(ctx):
            """Lists the user's active reminders.

            Args:
                ctx: The command context.

            """
            reminders = self.bot.storage.get("reminders", [])
            user_reminders = [r for r in reminders if r["user"] == ctx.sender]

            if not user_reminders:
                ctx.reply("You have no active reminders")
                return

            response = "Your reminders:\n"
            for i, reminder in enumerate(user_reminders, 1):
                remind_time = datetime.fromtimestamp(reminder["time"])
                response += f"{i}. {reminder['message']} (at {remind_time.strftime('%Y-%m-%d %H:%M:%S')})\n"

            ctx.reply(response)

    def _check_reminders(self):
        """Checks for reminders that are due and sends notifications."""
        reminders = self.bot.storage.get("reminders", [])
        current_time = time.time()

        due_reminders = [r for r in reminders if r["time"] <= current_time]
        remaining = [r for r in reminders if r["time"] > current_time]

        for reminder in due_reminders:
            self.bot.send(
                reminder["user"],
                f"Reminder: {reminder['message']}",
                "Reminder",
            )

        if due_reminders:
            self.bot.storage.set("reminders", remaining)

    def run(self):
        """Runs the bot."""
        self.bot.run()
