"""Templates module for LXMFy bot framework.

This module provides ready-to-use bot templates with different feature sets.
"""

from .cog_test_bot import CogTestBot
from .echo_bot import EchoBot
from .note_bot import NoteBot
from .reminder_bot import ReminderBot

__all__ = ["CogTestBot", "EchoBot", "NoteBot", "ReminderBot"]
