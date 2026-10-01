"""Spam protection module for LXMFy.

This module provides spam protection functionality for LXMFy bots,
including rate limiting, warning system, and user banning capabilities.
"""

from collections import defaultdict
from dataclasses import dataclass
from time import time

from .permissions import DefaultPerms


@dataclass
class SpamConfig:
    """Configuration settings for spam protection."""

    rate_limit: int = 5  # Maximum messages per cooldown period
    cooldown: int = 60  # Cooldown period in seconds
    max_warnings: int = 3  # Maximum warnings before ban
    warning_timeout: int = 300  # Time before warnings reset


class SpamProtection:
    """Spam protection system for LXMF bots.

    This class manages message rate limiting, user warnings, and bans to prevent
    spam abuse of the bot. It persists data across bot restarts using the provided
    storage system.

    Attributes:
        storage: Storage backend for persisting spam protection data
        message_counts: Dictionary tracking message timestamps per user
        warnings: Dictionary tracking warning counts per user
        banned_users: Set of banned user hashes
        warning_times: Dictionary tracking last warning time per user

    """

    def __init__(self, storage, bot, **kwargs):
        """Initialize spam protection with the given configuration.

        Args:
            storage: Storage backend for persisting data
            bot: Reference to the bot instance
            **kwargs: Override default spam configuration settings

        """
        self.storage = storage
        self.bot = bot
        self.config = SpamConfig(**kwargs)
        self.message_counts = defaultdict(list)
        self.command_counts = defaultdict(list)
        self.warnings = defaultdict(int)
        self.banned_users = set()
        self.warning_times = defaultdict(float)
        self.load_data()

    def load_data(self):
        """Load spam protection data from storage."""
        stored_counts = self.storage.get("spam:message_counts", {})
        self.message_counts = defaultdict(list, stored_counts)
        stored_command_counts = self.storage.get("spam:command_counts", {})
        self.command_counts = defaultdict(list, stored_command_counts)
        stored_warnings = self.storage.get("spam:warnings", {})
        self.warnings = defaultdict(int, stored_warnings)
        self.banned_users = set(self.storage.get("spam:banned_users", []))
        stored_times = self.storage.get("spam:warning_times", {})
        self.warning_times = defaultdict(float, stored_times)

    def save_data(self):
        """Save current spam protection data to storage."""
        self.storage.set("spam:message_counts", dict(self.message_counts))
        self.storage.set("spam:command_counts", dict(self.command_counts))
        self.storage.set("spam:warnings", dict(self.warnings))
        self.storage.set("spam:banned_users", list(self.banned_users))
        self.storage.set("spam:warning_times", dict(self.warning_times))

    def check_spam(self, sender) -> tuple[bool, str | None]:
        """Check if a message from the sender should be allowed.

        Args:
            sender: Hash of the message sender

        Returns:
            Tuple[bool, str]: (allowed, message) where allowed indicates if the message
            should be processed and message contains any warning/ban notification

        """
        # Check if user has bypass permission
        if self.bot.permissions.has_permission(sender, DefaultPerms.BYPASS_SPAM):
            return True, None

        if sender in self.banned_users:
            return False, "You are banned from using this bot."

        current_time = time()

        # Clean old messages
        self.message_counts[sender] = [
            t
            for t in self.message_counts[sender]
            if current_time - t <= self.config.cooldown
        ]

        # Check rate limit
        if len(self.message_counts[sender]) >= self.config.rate_limit:
            self.warnings[sender] += 1
            self.warning_times[sender] = current_time

            if self.warnings[sender] >= self.config.max_warnings:
                self.banned_users.add(sender)
                self.save_data()
                return False, "You have been banned for spamming."

            self.save_data()
            return (
                False,
                f"Rate limit exceeded. Warning {self.warnings[sender]}/{self.config.max_warnings}",
            )

        # Add new message timestamp
        self.message_counts[sender].append(current_time)

        # Reset warnings if warning_timeout has passed
        if (
            current_time - self.warning_times.get(sender, 0)
        ) > self.config.warning_timeout:
            self.warnings[sender] = 0

        self.save_data()
        return True, None

    def check_command_limit(
        self,
        sender,
        command: str,
        limit: int,
    ) -> tuple[bool, str | None]:
        """Check a per-command rate limit for a sender.

        Sliding window per (sender, command) pair sharing the global
        cooldown period. Unlike the global limit, hitting a command
        limit only rejects the invocation; it never warns or bans.

        Args:
            sender: Hash of the message sender
            command: Command name being invoked
            limit: Max invocations allowed inside the cooldown window

        Returns:
            Tuple[bool, str]: (allowed, message)

        """
        if limit <= 0:
            return True, None
        if self.bot.permissions.has_permission(sender, DefaultPerms.BYPASS_SPAM):
            return True, None

        key = f"{sender}:{command}"
        current_time = time()
        window = [
            t
            for t in self.command_counts[key]
            if current_time - t <= self.config.cooldown
        ]
        self.command_counts[key] = window

        if len(window) >= limit:
            retry_after = int(self.config.cooldown - (current_time - window[0])) + 1
            self.save_data()
            return (
                False,
                f"Command '{command}' is rate limited. Try again in {retry_after}s.",
            )

        window.append(current_time)
        self.save_data()
        return True, None

    def unban(self, sender) -> bool:
        """Remove a user from the ban list.

        Args:
            sender: Hash of the user to unban

        Returns:
            bool: True if the user was unbanned, False if they weren't banned

        """
        if sender in self.banned_users:
            self.banned_users.remove(sender)
            self.warnings[sender] = 0
            self.save_data()
            return True
        return False
