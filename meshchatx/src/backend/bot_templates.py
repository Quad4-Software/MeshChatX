# SPDX-License-Identifier: 0BSD

import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from lxmfy import IconAppearance, LXMFBot, pack_icon_appearance_field

from meshchatx.src.version import __version__ as meshchatx_version

logger = logging.getLogger("meshchatx.bots")

# Sentinel: no icon spec supplied, fall back to the template default.
_USE_DEFAULT_ICON = object()


def _pack_icon_field(icon):
    """Pack an icon spec into an LXMF icon appearance field dict.

    Accepts {icon_name, fg_color, bg_color} with #rrggbb colours and returns
    the packed lxmf_fields dict, or None when unset or malformed.
    """
    if not isinstance(icon, dict):
        return None
    try:
        appearance = IconAppearance(
            icon_name=str(icon["icon_name"]),
            fg_color=bytes.fromhex(str(icon["fg_color"]).lstrip("#")),
            bg_color=bytes.fromhex(str(icon["bg_color"]).lstrip("#")),
        )
        return pack_icon_appearance_field(appearance)
    except (KeyError, TypeError, ValueError):
        return None


def _resolve_icon_field(icon, default_icon):
    """Resolve the effective icon field.

    An explicit spec wins over the template default; no spec and no default
    means no icon.
    """
    if icon is _USE_DEFAULT_ICON:
        icon = default_icon
    return _pack_icon_field(icon)


def _lxmf_bot_kwargs(
    *,
    name,
    storage_path,
    test_mode,
    config_path,
    reticulum_config_dir,
    lxmf_settings=None,
    **extra,
):
    kwargs = {
        "name": name,
        "test_mode": test_mode,
        "storage_path": storage_path,
        "config_path": config_path,
        "reticulum_config_dir": reticulum_config_dir,
        **extra,
    }
    if lxmf_settings:
        kwargs.update(lxmf_settings)
    return kwargs


class StoppableBot:
    def __init__(self):
        self._stop_event = None

    def set_stop_event(self, stop_event):
        self._stop_event = stop_event

    def should_stop(self):
        return self._stop_event and self._stop_event.is_set()


class EchoBotTemplate(StoppableBot):
    DEFAULT_ICON: ClassVar[dict] = {
        "icon_name": "forum",
        "fg_color": "#add8e6",
        "bg_color": "#3b5998",
    }

    def __init__(
        self,
        name="Echo Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
        propagation_settings=None,
        lxmf_settings=None,
        icon=_USE_DEFAULT_ICON,
    ):
        super().__init__()

        merged = lxmf_settings if lxmf_settings is not None else propagation_settings

        self.bot = LXMFBot(
            **_lxmf_bot_kwargs(
                name=name,
                storage_path=storage_path,
                test_mode=test_mode,
                config_path=config_path,
                reticulum_config_dir=reticulum_config_dir,
                lxmf_settings=merged,
                announce=600,
                command_prefix="",
                first_message_enabled=True,
            ),
        )
        self.setup_commands()
        self.setup_message_handlers()

        self.icon_lxmf_field = _resolve_icon_field(icon, self.DEFAULT_ICON)

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
    DEFAULT_ICON: ClassVar[dict] = {
        "icon_name": "note-text",
        "fg_color": "#374151",
        "bg_color": "#fde68a",
    }

    def __init__(
        self,
        name="Note Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
        propagation_settings=None,
        lxmf_settings=None,
        icon=_USE_DEFAULT_ICON,
    ):
        super().__init__()

        merged = lxmf_settings if lxmf_settings is not None else propagation_settings

        self.bot = LXMFBot(
            **_lxmf_bot_kwargs(
                name=name,
                storage_path=storage_path or "data/notes",
                test_mode=test_mode,
                config_path=config_path,
                reticulum_config_dir=reticulum_config_dir,
                lxmf_settings=merged,
                announce=600,
                command_prefix="/",
                storage_type="json",
            ),
        )
        self.icon_lxmf_field = _resolve_icon_field(icon, self.DEFAULT_ICON)
        self.setup_commands()

    def setup_commands(self):
        @self.bot.command(name="note", description="Save a note")
        def save_note(ctx):
            if self.should_stop():
                return
            if not ctx.args:
                ctx.reply("Usage: /note <your note>", lxmf_fields=self.icon_lxmf_field)
                return

            note = {
                "text": " ".join(ctx.args),
                "timestamp": datetime.now(UTC).isoformat(),
                "tags": [w[1:] for w in ctx.args if w.startswith("#")],
            }

            notes = self.bot.storage.get(f"notes:{ctx.sender}", [])
            notes.append(note)
            self.bot.storage.set(f"notes:{ctx.sender}", notes)
            ctx.reply("Note saved!", lxmf_fields=self.icon_lxmf_field)

        @self.bot.command(name="notes", description="List your notes")
        def list_notes(ctx):
            if self.should_stop():
                return
            notes = self.bot.storage.get(f"notes:{ctx.sender}", [])
            if not notes:
                ctx.reply(
                    "You haven't saved any notes yet!",
                    lxmf_fields=self.icon_lxmf_field,
                )
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
                ctx.reply(response, lxmf_fields=self.icon_lxmf_field)
            elif ctx.args[0] == "all":
                response = "All Your Notes:\n"
                for i, note in enumerate(notes, 1):
                    tags = (
                        " ".join(f"#{tag}" for tag in note["tags"])
                        if note["tags"]
                        else ""
                    )
                    response += f"{i}. {note['text']} {tags}\n"
                ctx.reply(response, lxmf_fields=self.icon_lxmf_field)

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
    DEFAULT_ICON: ClassVar[dict] = {
        "icon_name": "alarm",
        "fg_color": "#ffffff",
        "bg_color": "#b45309",
    }

    def __init__(
        self,
        name="Reminder Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
        propagation_settings=None,
        lxmf_settings=None,
        icon=_USE_DEFAULT_ICON,
    ):
        super().__init__()

        merged = lxmf_settings if lxmf_settings is not None else propagation_settings

        self.bot = LXMFBot(
            **_lxmf_bot_kwargs(
                name=name,
                storage_path=storage_path or "data/reminders.db",
                test_mode=test_mode,
                config_path=config_path,
                reticulum_config_dir=reticulum_config_dir,
                lxmf_settings=merged,
                announce=600,
                command_prefix="/",
                storage_type="sqlite",
            ),
        )
        self.icon_lxmf_field = _resolve_icon_field(icon, self.DEFAULT_ICON)
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
                    lxmf_fields=self.icon_lxmf_field,
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
                    "Invalid time format. Use combinations of d, h, m",
                    lxmf_fields=self.icon_lxmf_field,
                )
                return

            remind_time = datetime.now(UTC) + timedelta(minutes=total_minutes)
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
                lxmf_fields=self.icon_lxmf_field,
            )

    def _check_reminders(self):
        if self.should_stop():
            return
        reminders = self.bot.storage.get("reminders", [])
        current_time = time.time()
        due_reminders = [r for r in reminders if r["time"] <= current_time]
        remaining = [r for r in reminders if r["time"] > current_time]

        for reminder in due_reminders:
            self.bot.send(
                reminder["user"],
                f"Reminder: {reminder['message']}",
                lxmf_fields=self.icon_lxmf_field,
            )

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


def _human_uptime(seconds):
    """Render a duration in seconds as a compact human string like 1d 2h 3m 4s."""
    remaining = max(0, int(seconds))
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, secs = divmod(remaining, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


class RRCBotTemplate(StoppableBot):
    """RRC room bot driven by LXMFy's hub client support.

    Answers prefixed commands (default "!") in hosted hub rooms. When
    mention_only is on it only reacts to messages that mention the bot nick,
    and a per-requester cooldown throttles replies.
    """

    DEFAULT_ICON: ClassVar[dict] = {
        "icon_name": "chat",
        "fg_color": "#d1fae5",
        "bg_color": "#065f46",
    }

    def __init__(
        self,
        name="RRC Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
        propagation_settings=None,
        lxmf_settings=None,
        rrc_hub=None,
        rrc_rooms=None,
        rrc_nick=None,
        rrc_mention_only=True,
        rrc_command_prefix="!",
        rrc_rate_seconds=8,
        icon=_USE_DEFAULT_ICON,
    ):
        super().__init__()
        if not rrc_hub:
            msg = "rrc_hub is required"
            raise ValueError(msg)

        merged = lxmf_settings if lxmf_settings is not None else propagation_settings

        self.name = name
        self.rrc_hub = str(rrc_hub).strip().lower()
        self.rrc_rooms = []
        for raw in rrc_rooms or []:
            room = str(raw).strip().lstrip("#").strip()
            if room:
                self.rrc_rooms.append(room)
        self.rrc_nick = str(rrc_nick).strip() if rrc_nick else name
        self.rrc_mention_only = bool(rrc_mention_only)
        self.rrc_command_prefix = str(rrc_command_prefix or "!")
        try:
            self.rrc_rate_seconds = max(0, int(rrc_rate_seconds))
        except (TypeError, ValueError):
            self.rrc_rate_seconds = 8
        self._started_at = time.time()
        self._last_reply = {}

        self.bot = LXMFBot(
            **_lxmf_bot_kwargs(
                name=name,
                storage_path=storage_path or "data/rrc_bot",
                test_mode=test_mode,
                config_path=config_path,
                reticulum_config_dir=reticulum_config_dir,
                lxmf_settings=merged,
                announce=600,
                rrc_enabled=True,
                rrc_hubs=[self.rrc_hub],
                rrc_rooms=list(self.rrc_rooms),
                rrc_nick=self.rrc_nick,
            ),
        )
        self.icon_lxmf_field = _resolve_icon_field(icon, self.DEFAULT_ICON)
        self.setup_rrc_handlers()

    def setup_rrc_handlers(self):
        @self.bot.on_rrc()
        def _on_rrc_event(event, client, payload):
            self._handle_rrc_event(event, client, payload)

    def _help_text(self):
        p = self.rrc_command_prefix
        return f"commands: {p}uptime, {p}ping, {p}status, {p}help"

    def _status_text(self):
        rooms = ", ".join(self.rrc_rooms) if self.rrc_rooms else "(none)"
        return (
            f"{self.name} on hub {self.rrc_hub}; rooms: {rooms}; "
            f"up {_human_uptime(time.time() - self._started_at)}; "
            f"meshchatx {meshchatx_version}"
        )

    def _handle_rrc_event(self, event, client, payload):
        if event != "msg" or self.should_stop() or payload is None:
            return

        own = getattr(getattr(self.bot, "identity", None), "hash", None)
        src = getattr(payload, "src", None)
        if (
            own is not None
            and isinstance(src, (bytes, bytearray))
            and bytes(src) == bytes(own)
        ):
            return

        room = getattr(payload, "room", None)
        if not room:
            return
        text = getattr(payload, "text", "") or ""
        nick = getattr(payload, "nick", None) or "anon"

        mentioned = bool(getattr(payload, "mention", False))
        if not mentioned and self.rrc_nick:
            mentioned = ("@" + self.rrc_nick).lower() in text.lower()
        if self.rrc_mention_only and not mentioned:
            return

        body = text.strip()
        if mentioned and self.rrc_nick:
            body = re.sub(
                r"(?<![A-Za-z0-9_])@" + re.escape(self.rrc_nick) + r"(?![A-Za-z0-9_])",
                " ",
                body,
                flags=re.IGNORECASE,
            ).strip()
        if body.startswith(self.rrc_command_prefix):
            body = body[len(self.rrc_command_prefix) :].strip()
        else:
            tokens = body.split()
            prefixed = next(
                (
                    i
                    for i, tok in enumerate(tokens)
                    if tok.startswith(self.rrc_command_prefix)
                ),
                None,
            )
            if prefixed is not None:
                body = " ".join(tokens[prefixed:])[
                    len(self.rrc_command_prefix) :
                ].strip()
            elif self.rrc_mention_only and mentioned:
                pass
            else:
                return

        parts = body.split()
        if not parts:
            self._reply(client, room, nick, src, self._help_text())
            return
        cmd = parts[0].lower()
        if cmd == "uptime":
            reply = "up " + _human_uptime(time.time() - self._started_at)
        elif cmd == "ping":
            reply = "pong"
        elif cmd == "help":
            reply = self._help_text()
        elif cmd in ("status", "about"):
            reply = self._status_text()
        else:
            reply = f"unknown command '{cmd}' - try " + self.rrc_command_prefix + "help"
        self._reply(client, room, nick, src, reply)

    def _reply(self, client, room, nick, src, text):
        if isinstance(src, (bytes, bytearray)):
            key = bytes(src).hex()
        elif src is not None:
            key = str(src)
        else:
            key = str(nick)
        now = time.time()
        last = self._last_reply.get(key)
        if last is not None and now - last < self.rrc_rate_seconds:
            return
        self._last_reply[key] = now
        try:
            client.send_message(room, f"@{nick} {text}")
        except Exception as exc:
            logger.warning("RRC bot reply to %s failed: %s", room, exc)

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


class CustomBotTemplate(StoppableBot):
    """User-defined command bot with canned replies.

    Commands map names to fixed response text, plus an optional first-contact
    welcome message.
    """

    DEFAULT_ICON: ClassVar[dict] = {
        "icon_name": "robot",
        "fg_color": "#e0e7ff",
        "bg_color": "#4338ca",
    }

    def __init__(
        self,
        name="Custom Bot",
        storage_path=None,
        test_mode=False,
        config_path=None,
        reticulum_config_dir=None,
        propagation_settings=None,
        lxmf_settings=None,
        icon=_USE_DEFAULT_ICON,
        custom=None,
    ):
        super().__init__()

        merged = lxmf_settings if lxmf_settings is not None else propagation_settings

        custom = custom or {}
        self.custom_commands = [
            {
                "name": str(c["name"]),
                "response": str(c["response"]),
                "description": str(c.get("description") or "Custom command"),
            }
            for c in (custom.get("commands") or [])
            if isinstance(c, dict) and c.get("name") and c.get("response")
        ]
        welcome = custom.get("welcome")
        self.welcome_message = (
            str(welcome).strip()
            if isinstance(welcome, str) and welcome.strip()
            else None
        )

        self.bot = LXMFBot(
            **_lxmf_bot_kwargs(
                name=name,
                storage_path=storage_path or "data/custom",
                test_mode=test_mode,
                config_path=config_path,
                reticulum_config_dir=reticulum_config_dir,
                lxmf_settings=merged,
                announce=600,
                command_prefix="!",
                storage_type="json",
                first_message_enabled=True,
            ),
        )
        self.icon_lxmf_field = _resolve_icon_field(icon, self.DEFAULT_ICON)
        self.setup_commands()

    def setup_commands(self):
        if self.welcome_message:

            @self.bot.on_first_message()
            def welcome(sender, message):
                if self.should_stop():
                    return True
                self.bot.send(
                    sender,
                    self.welcome_message,
                    lxmf_fields=self.icon_lxmf_field,
                )
                return True

        for spec in self.custom_commands:
            self._register_custom_command(spec)

        if not any(c["name"].lower() == "help" for c in self.custom_commands):

            @self.bot.command(name="help", description="List available commands")
            def help_command(ctx):
                if self.should_stop():
                    return
                names = sorted({c["name"] for c in self.custom_commands})
                if not names:
                    ctx.reply(
                        "No commands configured.",
                        lxmf_fields=self.icon_lxmf_field,
                    )
                    return
                prefix = self.bot.config.command_prefix
                ctx.reply(
                    "Commands: " + ", ".join(prefix + n for n in names),
                    lxmf_fields=self.icon_lxmf_field,
                )

    def _register_custom_command(self, spec):
        response = spec["response"]

        @self.bot.command(name=spec["name"], description=spec["description"])
        def _custom_command(ctx, _response=response):
            if self.should_stop():
                return
            ctx.reply(_response, lxmf_fields=self.icon_lxmf_field)

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
