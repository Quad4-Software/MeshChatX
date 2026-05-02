"""Command handling module for LXMFy.

This module provides the core command handling functionality for LXMFy bots,
including command registration, method decoration, and cog support.
"""

from dataclasses import dataclass

from .permissions import BasePermission, DefaultPerms


@dataclass
class CommandHelp:
    """Help metadata for a command"""

    name: str
    description: str
    usage: str | None = None
    examples: list[str] = None
    category: str | None = None
    aliases: list[str] = None


class Command:
    """A decorator class for bot commands.

    This class is used to mark methods as bot commands and provide metadata
    about the command such as its name, description, and permission requirements.

    Attributes:
        name (str): The name of the command
        description (str): A description of what the command does
        admin_only (bool): Whether the command is restricted to admin users
        callback (callable): The function that implements the command

    """

    def __init__(
        self,
        name,
        description="No description provided",
        admin_only=False,
        permissions: BasePermission | None = None,
        usage=None,
        examples=None,
        category=None,
        aliases=None,
        threaded: bool = False,
    ):
        """Initialize a new Command.

        Args:
            name (str): The name of the command
            description (str, optional): Description of the command. Defaults to "No description provided"
            admin_only (bool, optional): Whether the command requires admin privileges. Defaults to False

        """
        self.name = name
        self.description = description
        self.admin_only = admin_only
        self.permissions = permissions or (
            DefaultPerms.ALL if admin_only else DefaultPerms.USE_COMMANDS
        )
        self.threaded = threaded
        self.callback = None
        self.help = CommandHelp(
            name=name,
            description=description,
            usage=usage,
            examples=examples or [],
            category=category,
            aliases=aliases or [],
        )

    def __call__(self, func):
        """Decorate a function as a command.

        Args:
            func (callable): The function to be decorated

        Returns:
            callable: The decorated function

        """
        self.callback = func
        func.command = self
        return func

    def __get__(self, obj, objtype=None):
        """Support instance methods in command definitions.

        This method enables the command decorator to work with instance methods
        by properly binding the method to the instance.

        Args:
            obj: The instance that the command is bound to
            objtype: The type of the instance

        Returns:
            Command: A new Command instance bound to the object

        """
        if obj is None:
            return self
        new_cmd = self.__class__(
            name=self.name,
            description=self.description,
            admin_only=self.admin_only,
            permissions=self.permissions,
            usage=self.help.usage,
            examples=self.help.examples,
            category=self.help.category,
            aliases=self.help.aliases,
            threaded=self.threaded,
        )
        new_cmd.callback = self.callback.__get__(obj, objtype)
        return new_cmd


def command(*args, **kwargs):
    """Shorthand decorator for creating Command instances.

    This function provides a more concise way to create commands using the
    @command decorator syntax instead of @Command().

    Args:
        *args: Positional arguments to pass to Command constructor
        **kwargs: Keyword arguments to pass to Command constructor

    Returns:
        Command: A new Command instance

    """
    return Command(*args, **kwargs)


class Cog:
    """Base class for bot extension modules (cogs).

    Cogs are used to organize bot commands and listeners into modular components.
    Each cog represents a collection of related commands and functionality.

    Attributes:
        bot: The bot instance that this cog is attached to

    """

    def __init__(self, bot):
        """Initialize a new Cog.

        Args:
            bot: The bot instance that this cog will be registered to

        """
        self.bot = bot

    def has_permission(self, user: str, permission: DefaultPerms) -> bool:
        """Check if user has specific permission"""
        if not self.enabled:  # If permissions are disabled, allow everything
            return True
        user_perms = self.get_user_permissions(user)
        return bool(user_perms & permission)
