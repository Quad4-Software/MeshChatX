"""Command registration and execution for LXMFBot."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from ._sync import run_sync
from .commands import Command
from .middleware import MiddlewareType

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable
    from concurrent.futures import ThreadPoolExecutor

    from .config import BotConfig
    from .middleware import MiddlewareManager
    from .moderation import SpamProtection
    from .permissions import PermissionManager

F = TypeVar("F", bound=Callable)


class DispatchMixin:
    """Command decorator, admin check, and command execution."""

    admins: set
    commands: dict
    config: BotConfig
    logger: logging.Logger
    middleware: MiddlewareManager
    permissions: PermissionManager
    spam_protection: SpamProtection
    thread_pool: ThreadPoolExecutor
    send: Callable[..., bool]

    def command(self, *args, **kwargs) -> Callable[[F], F]:
        """Decorator for registering commands.

        Args:
            *args: Command name (optional).
            **kwargs: Forwarded to Command: name, description, admin_only,
                permissions, usage, examples, category, aliases,
                threaded, rate_limit.

        """

        def decorator(func: F) -> F:
            """The actual decorator that registers the command."""
            name = args[0] if len(args) > 0 else kwargs.pop("name", func.__name__)

            cmd = Command(name=name, **kwargs)
            cmd.callback = func
            self.commands[name] = cmd
            return func

        return decorator

    def is_admin(self, sender):
        """Check if a sender is an admin.

        Args:
            sender: The sender's identity hash.

        Returns:
            True if the sender is an admin, False otherwise.

        """
        return sender in self.admins

    def _execute_command(self, cmd_name: str, args: list, msg) -> bool:
        """Execute a registered command by name.

        Returns:
            True if the command was found and executed (or raised an error),
            False if no command with that name exists.

        """
        if cmd_name not in self.commands:
            return False

        cmd = self.commands[cmd_name]

        if not self.permissions.has_permission(msg.sender, cmd.permissions):
            self.send(msg.sender, "You don't have permission to use this command.")
            return True

        if cmd.rate_limit is not None and cmd.rate_limit > 0:
            allowed, notice = self.spam_protection.check_command_limit(
                msg.sender,
                cmd_name,
                cmd.rate_limit,
            )
            if not allowed:
                if notice:
                    self.send(msg.sender, notice)
                return True

        try:
            sig = inspect.signature(cmd.callback)
            params = list(sig.parameters.values())

            converted_args = []
            for i, arg_val in enumerate(args):
                param_idx = i + 1
                if param_idx < len(params):
                    param = params[param_idx]
                    annotation = param.annotation
                    if (
                        annotation != inspect.Parameter.empty
                        and callable(annotation)
                        and not isinstance(annotation, str)
                    ):
                        try:
                            converted_args.append(annotation(arg_val))
                        except (ValueError, TypeError):
                            converted_args.append(arg_val)
                    else:
                        converted_args.append(arg_val)
                else:
                    converted_args.append(arg_val)

            msg.args = converted_args
            msg.is_admin = msg.sender in self.admins

            try:
                if cmd.threaded:
                    self.thread_pool.submit(run_sync, cmd.callback, msg)
                else:
                    run_sync(cmd.callback, msg)
            finally:
                self.middleware.execute(MiddlewareType.POST_COMMAND, msg)
            return True

        except Exception as e:
            self.logger.exception("Error executing command %s", cmd_name)
            self.send(msg.sender, f"Error executing command: {e}")
            return True
