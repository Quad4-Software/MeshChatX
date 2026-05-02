"""LXMFy - A bot framework for creating LXMF bots on the Reticulum Network.

This package provides tools and utilities for creating and managing LXMF bots,
including command handling, storage management, moderation features, and role-based permissions.
"""

from .attachments import (
    Attachment,
    AttachmentType,
    IconAppearance,
    pack_attachment,
    pack_icon_appearance_field,
)
from .cogs_core import load_cogs_from_directory
from .commands import Command, command
from .config import BotConfig
from .core import LXMFBot, BOT_DISPLAY_NAME_FILE
from .events import Event, EventManager, EventPriority
from .help import HelpFormatter, HelpSystem
from .middleware import MiddlewareContext, MiddlewareManager, MiddlewareType
from .permissions import DefaultPerms, PermissionManager, Role
from .scheduler import ScheduledTask, TaskScheduler
from .storage import JSONStorage, SQLiteStorage, Storage
from .validation import format_validation_results, validate_bot

__all__ = [
    "Attachment",
    "AttachmentType",
    "BotConfig",
    "Command",
    "DefaultPerms",
    "Event",
    "EventManager",
    "EventPriority",
    "HelpFormatter",
    "HelpSystem",
    "IconAppearance",
    "JSONStorage",
    "LXMFBot",
    "BOT_DISPLAY_NAME_FILE",
    "MiddlewareContext",
    "MiddlewareManager",
    "MiddlewareType",
    "PermissionManager",
    "Role",
    "SQLiteStorage",
    "ScheduledTask",
    "Storage",
    "TaskScheduler",
    "__version__",
    "command",
    "format_validation_results",
    "load_cogs_from_directory",
    "pack_attachment",
    "pack_icon_appearance_field",
    "validate_bot",
]

from .__version__ import __version__
