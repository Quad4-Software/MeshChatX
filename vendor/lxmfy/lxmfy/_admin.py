"""Built-in admin commands for LXMFBot.

Registers queue inspection, outbound cancel, and extension management
commands gated to configured admins.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import LXMFBot

_MAX_LISTED = 20


def _short(value, keep: int = 16) -> str:
    text = str(value) if value is not None else "?"
    return text if len(text) <= keep else f"{text[:keep]}..."


def _prefix(bot) -> str:
    return bot.command_prefix if bot.command_prefix else "/"


def register_admin_commands(bot: LXMFBot) -> None:
    """Register the built-in admin command set on a bot."""

    @bot.command(
        name="queue",
        description="List pending outbound messages",
        admin_only=True,
    )
    def queue_command(ctx):
        entries = bot.outbound_queue()
        internal = bot.queue.qsize()
        pending = bot.storage.get("pending_sends", [])
        if not isinstance(pending, list):
            pending = []

        lines = [
            f"router outbound: {len(entries)}",
            f"internal queue: {internal}",
            f"held (unknown peers): {len(pending)}",
        ]
        for index, entry in enumerate(entries[:_MAX_LISTED], start=1):
            progress = entry.get("progress")
            pct = (
                f"{int(100 * progress)}%" if isinstance(progress, (int, float)) else "-"
            )
            lines.append(
                f"{index}. {_short(entry.get('destination'))} "
                f"state={entry.get('state')} {pct} "
                f"id={_short(entry.get('message_id'), 32)}",
            )
        if len(entries) > _MAX_LISTED:
            lines.append(f"... {len(entries) - _MAX_LISTED} more")
        if not entries and internal:
            lines.append("internal queue drains into the router on the next run cycle")
        ctx.reply("\n".join(lines))

    @bot.command(
        name="cancel",
        description="Cancel a pending outbound message",
        admin_only=True,
    )
    def cancel_command(ctx):
        if not ctx.args:
            ctx.reply(f"Usage: {_prefix(bot)}cancel <message_id|all>")
            return
        target = str(ctx.args[0]).strip()

        if target == "all":
            cancelled = 0
            for entry in bot.outbound_queue():
                message_id = entry.get("message_id")
                if message_id and bot.cancel_outbound(message_id):
                    cancelled += 1
            ctx.reply(f"Cancelled {cancelled} outbound message(s).")
            return

        if bot.cancel_outbound(target):
            ctx.reply("Cancelled.")
        else:
            ctx.reply(
                "Not cancelled: no pending message with that id. "
                f"Run {_prefix(bot)}queue to list ids.",
            )

    @bot.command(
        name="loadext",
        description="Load a cog extension by module name",
        admin_only=True,
    )
    def loadext_command(ctx):
        if not ctx.args:
            ctx.reply(f"Usage: {_prefix(bot)}loadext <name>")
            return
        name = str(ctx.args[0]).strip()
        try:
            bot.load_extension(name)
        except Exception as e:
            ctx.reply(f"Failed to load {name}: {e}")
            return
        ctx.reply(f"Loaded {name}.")

    @bot.command(
        name="reloadext",
        description="Reload a loaded cog extension",
        admin_only=True,
    )
    def reloadext_command(ctx):
        if not ctx.args:
            ctx.reply(f"Usage: {_prefix(bot)}reloadext <name>")
            return
        name = str(ctx.args[0]).strip()
        try:
            bot.reload_extension(name)
        except Exception as e:
            ctx.reply(f"Failed to reload {name}: {e}")
            return
        ctx.reply(f"Reloaded {name}.")

    @bot.command(
        name="inbox",
        description="List inbound transfers or cancel one by hash",
        admin_only=True,
    )
    def inbox_command(ctx):
        if ctx.args:
            action = str(ctx.args[0]).strip().lower()
            if action == "cancel":
                if len(ctx.args) > 1 and str(ctx.args[1]).strip() == "all":
                    count = bot.cancel_all_inbound()
                    ctx.reply(f"Cancelled {count} inbound transfer(s).")
                    return
                if len(ctx.args) < 2:
                    ctx.reply(
                        f"Usage: {_prefix(bot)}inbox cancel <resource_hash|all>",
                    )
                    return
                target = str(ctx.args[1]).strip()
                if bot.cancel_inbound(target):
                    ctx.reply("Cancelled.")
                else:
                    ctx.reply(
                        "Not cancelled: no active inbound transfer with that hash.",
                    )
                return
            ctx.reply(f"Usage: {_prefix(bot)}inbox [cancel <hash|all>]")
            return

        transfers = bot.inbound_transfers()
        lines = [f"active inbound transfers: {bot.inbound_count()}"]
        for index, entry in enumerate(transfers[:_MAX_LISTED], start=1):
            progress = entry.get("progress")
            pct = (
                f"{int(100 * progress)}%" if isinstance(progress, (int, float)) else "-"
            )
            size = entry.get("size")
            size_text = f" {size}B" if isinstance(size, int) else ""
            lines.append(
                f"{index}. {_short(entry.get('hash'), 32)} "
                f"{pct}{size_text} status={entry.get('status')}",
            )
        if len(transfers) > _MAX_LISTED:
            lines.append(f"... {len(transfers) - _MAX_LISTED} more")
        ctx.reply("\n".join(lines))

    @bot.command(
        name="delivery",
        description="Show recent outbound delivery events",
        admin_only=True,
    )
    def delivery_command(ctx):
        limit = 15
        if ctx.args:
            with contextlib.suppress(TypeError, ValueError):
                limit = max(1, min(50, int(ctx.args[0])))
        ctx.reply(
            format_delivery_timeline(bot.delivery.recent(limit), limit=limit),
        )


def format_delivery_timeline(events: list[dict], limit: int = 15) -> str:
    """Render recent delivery events for chat or reports."""
    if not events:
        return "No delivery events recorded."
    lines = []
    for event in events[-limit:]:
        stage = event.get("stage", "?")
        dest = _short(event.get("destination"))
        reason = event.get("reason")
        suffix = f" ({reason})" if reason else ""
        lines.append(f"{stage} {dest}{suffix}")
    return "\n".join(lines)
