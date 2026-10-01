"""Cog and extension management for LXMFBot."""

from __future__ import annotations

import importlib
import inspect
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging

    from .config import BotConfig


class CogMixin:
    """Extension loading, cog registration, and hot reload."""

    cogs: dict
    commands: dict
    config: BotConfig
    hot_reloading: bool
    logger: logging.Logger

    def load_extension(self, name: str) -> None:
        """Load an extension (cog) by name.

        Args:
            name: The name of the extension to load.

        Raises:
            ValueError: If the module name contains invalid characters.
            ImportError: If the extension is missing setup function or fails to load.

        """
        if not re.match(r"^[a-zA-Z0-9_\.]+$", name):
            raise ValueError(f"Invalid module name format: {name}")

        if not name.startswith("cogs."):
            name = f"cogs.{name}"

        before_commands = set(self.commands)
        before_cogs = set(self.cogs)
        try:
            if self.hot_reloading and name in sys.modules:
                module = importlib.reload(sys.modules[name])
            else:
                module = importlib.import_module(name)

            if not hasattr(module, "setup"):
                raise ImportError(f"Extension {name} missing setup function")
            module.setup(self)
        except ImportError as e:
            raise ImportError(f"Failed to load extension {name}: {e!s}") from e
        except Exception:
            for cmd_name in set(self.commands) - before_commands:
                self.commands.pop(cmd_name, None)
            for cog_name in set(self.cogs) - before_cogs:
                self.cogs.pop(cog_name, None)
            raise

    def add_cog(self, cog):
        """Add a cog to the bot.

        Args:
            cog: The cog instance to add.

        """
        self.cogs[cog.__class__.__name__] = cog
        for _name, method in inspect.getmembers(
            cog,
            predicate=lambda x: hasattr(x, "command"),
        ):
            if _name.startswith("_") or _name == "bot":
                continue

            try:
                cmd_descriptor = method.command

                if hasattr(cmd_descriptor, "__get__") and hasattr(
                    cmd_descriptor,
                    "name",
                ):
                    cmd = cmd_descriptor.__get__(cog, cog.__class__)
                elif hasattr(cmd_descriptor, "name"):
                    cmd = cmd_descriptor
                    if cmd.callback is None:
                        cmd.callback = method
                else:
                    self.logger.warning(
                        "Unexpected command type for %s: %s",
                        _name,
                        type(cmd_descriptor),
                    )
                    continue

                self.commands[cmd.name] = cmd
            except Exception:
                self.logger.exception(
                    "Error adding command %s from cog %s", _name, cog.__class__.__name__
                )
                continue

    def remove_cog(self, cog_name: str) -> None:
        """Remove a cog from the bot by its class name.

        Args:
            cog_name: The name of the cog class to remove.

        """
        if cog_name in self.cogs:
            cog = self.cogs.pop(cog_name)
            # Remove commands bound to the cog instance or defined in its module
            commands_to_remove = [
                name
                for name, cmd in self.commands.items()
                if hasattr(cmd, "callback")
                and (
                    getattr(cmd.callback, "__self__", None) == cog
                    or getattr(cmd.callback, "__module__", None) == cog.__module__
                )
            ]
            for name in commands_to_remove:
                del self.commands[name]

    def reload_extension(self, name: str) -> None:
        """Reload an extension (cog) by name."""
        ext_name = name if name.startswith("cogs.") else f"cogs.{name}"

        # Find the cog associated with this extension to remove it first
        for cname, cog in list(self.cogs.items()):
            if cog.__module__ == ext_name:
                self.remove_cog(cname)
                break

        self.load_extension(name)
