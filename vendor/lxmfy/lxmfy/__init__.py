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
from .conversations import Answer, ConversationManager
from .core import BOT_DISPLAY_NAME_FILE, LXMFBot
from .debugger import (
    CheckResult,
    Debugger,
    DestinationProbe,
    DoctorReport,
    MessageDebugger,
    build_verdict,
    diagnose_destination,
    sort_checks_by_severity,
)
from .delivery import DeliveryTracker
from .events import Event, EventManager, EventPriority
from .help import HelpFormatter, HelpSystem
from .lxmf_fields import (
    FIELD_COMMANDS,
    FIELD_REACTION,
    FIELD_REPLY_QUOTE,
    FIELD_REPLY_TO,
    FIELD_RESULTS,
    FIELD_THREAD,
    REACTION_CONTENT,
    REACTION_TO,
    pack_reaction,
    pack_reply,
    pack_result,
    unpack_commands,
    unpack_reaction,
    unpack_reply,
)
from .middleware import MiddlewareContext, MiddlewareManager, MiddlewareType
from .permissions import DefaultPerms, PermissionManager, Role
from .rrc import (
    DEFAULT_DEST_NAME,
    RRC_VERSION,
    RRCClient,
    RRCManager,
    RRCMessage,
    decode_envelope,
    encode_envelope,
    make_envelope,
    normalize_room,
    validate_envelope,
)
from .scheduler import ScheduledTask, TaskScheduler
from .storage import JSONStorage, MsgPackStorage, SQLiteStorage, Storage
from .testing import SentMessage, TestBot, fake_message
from .validation import format_validation_results, validate_bot

__all__ = [
    "BOT_DISPLAY_NAME_FILE",
    "DEFAULT_DEST_NAME",
    "FIELD_COMMANDS",
    "FIELD_REACTION",
    "FIELD_REPLY_QUOTE",
    "FIELD_REPLY_TO",
    "FIELD_RESULTS",
    "FIELD_THREAD",
    "REACTION_CONTENT",
    "REACTION_TO",
    "RRC_VERSION",
    "Answer",
    "Attachment",
    "AttachmentType",
    "BotConfig",
    "CheckResult",
    "Command",
    "ConversationManager",
    "Debugger",
    "DefaultPerms",
    "DeliveryTracker",
    "DestinationProbe",
    "DoctorReport",
    "Event",
    "EventManager",
    "EventPriority",
    "HelpFormatter",
    "HelpSystem",
    "IconAppearance",
    "JSONStorage",
    "LXMFBot",
    "MessageDebugger",
    "MiddlewareContext",
    "MiddlewareManager",
    "MiddlewareType",
    "MsgPackStorage",
    "PermissionManager",
    "RRCClient",
    "RRCManager",
    "RRCMessage",
    "Role",
    "SQLiteStorage",
    "ScheduledTask",
    "SentMessage",
    "Storage",
    "TaskScheduler",
    "TestBot",
    "__version__",
    "build_verdict",
    "command",
    "decode_envelope",
    "diagnose_destination",
    "encode_envelope",
    "fake_message",
    "format_validation_results",
    "load_cogs_from_directory",
    "make_envelope",
    "normalize_room",
    "pack_attachment",
    "pack_icon_appearance_field",
    "pack_reaction",
    "pack_reply",
    "pack_result",
    "sort_checks_by_severity",
    "unpack_commands",
    "unpack_reaction",
    "unpack_reply",
    "validate_bot",
    "validate_envelope",
]

from .__version__ import __version__
