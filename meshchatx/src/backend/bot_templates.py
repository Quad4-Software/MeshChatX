import re
import time
from datetime import datetime, timedelta

from lxmfy import IconAppearance, LXMFBot, pack_icon_appearance_field

HAS_LXMFY = True


class StoppableBot:
    def __init__(self):
        self._stop_event = None

    def set_stop_event(self, stop_event):
        self._stop_event = stop_event

    def should_stop(self):
        return self._stop_event and self._stop_event.is_set()


class EchoBotTemplate(StoppableBot):
    def __init__(
        self,
        name="Echo Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
    ):
        super().__init__()

        self.bot = LXMFBot(
            name=name,
            announce=600,
            command_prefix="",
            first_message_enabled=True,
            test_mode=test_mode,
            storage_path=storage_path,
            config_path=config_path,
            reticulum_config_dir=reticulum_config_dir,
        )
        self.setup_commands()
        self.setup_message_handlers()

        icon_data = IconAppearance(
            icon_name="forum",
            fg_color=b"\xad\xd8\xe6",
            bg_color=b"\x3b\x59\x98",
        )
        self.icon_lxmf_field = pack_icon_appearance_field(icon_data)

    def setup_message_handlers(self):
        @self.bot.on_message()
        def echo_non_command_messages(sender, message):
            if self.should_stop():
                return True
            content = message.content.decode("utf-8").strip()
            if not content:
                return False

            command_name = content.split()[0]
            if command_name in self.bot.commands:
                return False

            self.bot.send(
                sender,
                content,
                lxmf_fields=self.icon_lxmf_field,
            )
            return False

    def setup_commands(self):
        @self.bot.command(name="echo", description="Echo back your message")
        def echo(ctx):
            if self.should_stop():
                return
            if ctx.args:
                ctx.reply(" ".join(ctx.args), lxmf_fields=self.icon_lxmf_field)
            else:
                ctx.reply("Usage: echo <message>", lxmf_fields=self.icon_lxmf_field)

        @self.bot.on_first_message()
        def welcome(sender, message):
            if self.should_stop():
                return True
            content = message.content.decode("utf-8").strip()
            self.bot.send(
                sender,
                f"Hi! I'm an echo bot, You said: {content}\n\n"
                "Try: echo <message> to make me repeat things!",
                lxmf_fields=self.icon_lxmf_field,
            )
            return True

    def run(self):
        self.bot.scheduler.start()
        try:
            while not self.should_stop():
                for _ in range(self.bot.queue.qsize()):
                    lxm = self.bot.queue.get()
                    if self.bot.router:
                        self.bot.router.handle_outbound(lxm)
                time.sleep(1)
        finally:
            self.bot.cleanup()


class NoteBotTemplate(StoppableBot):
    def __init__(
        self,
        name="Note Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
    ):
        super().__init__()

        self.bot = LXMFBot(
            name=name,
            announce=600,
            command_prefix="/",
            storage_type="json",
            storage_path=storage_path or "data/notes",
            test_mode=test_mode,
            config_path=config_path,
            reticulum_config_dir=reticulum_config_dir,
        )
        self.setup_commands()

    def setup_commands(self):
        @self.bot.command(name="note", description="Save a note")
        def save_note(ctx):
            if self.should_stop():
                return
            if not ctx.args:
                ctx.reply("Usage: /note <your note>")
                return

            note = {
                "text": " ".join(ctx.args),
                "timestamp": datetime.now().isoformat(),
                "tags": [w[1:] for w in ctx.args if w.startswith("#")],
            }

            notes = self.bot.storage.get(f"notes:{ctx.sender}", [])
            notes.append(note)
            self.bot.storage.set(f"notes:{ctx.sender}", notes)
            ctx.reply("Note saved!")

        @self.bot.command(name="notes", description="List your notes")
        def list_notes(ctx):
            if self.should_stop():
                return
            notes = self.bot.storage.get(f"notes:{ctx.sender}", [])
            if not notes:
                ctx.reply("You haven't saved any notes yet!")
                return

            if not ctx.args:
                response = "Your Notes:\n"
                for i, note in enumerate(notes[-10:], 1):
                    tags = (
                        " ".join(f"#{tag}" for tag in note["tags"])
                        if note["tags"]
                        else ""
                    )
                    response += f"{i}. {note['text']} {tags}\n"
                if len(notes) > 10:
                    response += f"\nShowing last 10 of {len(notes)} notes. Use /notes all to see all."
                ctx.reply(response)
            elif ctx.args[0] == "all":
                response = "All Your Notes:\n"
                for i, note in enumerate(notes, 1):
                    tags = (
                        " ".join(f"#{tag}" for tag in note["tags"])
                        if note["tags"]
                        else ""
                    )
                    response += f"{i}. {note['text']} {tags}\n"
                ctx.reply(response)

    def run(self):
        self.bot.scheduler.start()
        try:
            while not self.should_stop():
                for _ in range(self.bot.queue.qsize()):
                    lxm = self.bot.queue.get()
                    if self.bot.router:
                        self.bot.router.handle_outbound(lxm)
                time.sleep(1)
        finally:
            self.bot.cleanup()


class ReminderBotTemplate(StoppableBot):
    def __init__(
        self,
        name="Reminder Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
    ):
        super().__init__()

        self.bot = LXMFBot(
            name=name,
            announce=600,
            command_prefix="/",
            storage_type="sqlite",
            storage_path=storage_path or "data/reminders.db",
            test_mode=test_mode,
            config_path=config_path,
            reticulum_config_dir=reticulum_config_dir,
        )
        self.setup_commands()
        self.bot.scheduler.add_task(
            "check_reminders",
            self._check_reminders,
            "*/1 * * * *",
        )

    def setup_commands(self):
        @self.bot.command(name="remind", description="Set a reminder")
        def remind(ctx):
            if self.should_stop():
                return
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
                ctx.reply("Invalid time format. Use combinations of d, h, m")
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

    def _check_reminders(self):
        if self.should_stop():
            return
        reminders = self.bot.storage.get("reminders", [])
        current_time = time.time()
        due_reminders = [r for r in reminders if r["time"] <= current_time]
        remaining = [r for r in reminders if r["time"] > current_time]

        for reminder in due_reminders:
            self.bot.send(reminder["user"], f"Reminder: {reminder['message']}")

        if due_reminders:
            self.bot.storage.set("reminders", remaining)

    def run(self):
        self.bot.scheduler.start()
        try:
            while not self.should_stop():
                for _ in range(self.bot.queue.qsize()):
                    lxm = self.bot.queue.get()
                    if self.bot.router:
                        self.bot.router.handle_outbound(lxm)
                time.sleep(1)
        finally:
            self.bot.cleanup()
