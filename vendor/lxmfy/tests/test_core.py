"""Tests for LXMFy core functionality."""

from pathlib import Path

import RNS

from lxmfy import BOT_DISPLAY_NAME_FILE, BotConfig, LXMFBot
from lxmfy.commands import Command


class TestBotConfig:
    """Test BotConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BotConfig()
        assert config.name == "LXMFBot"
        assert config.announce == 600
        assert config.announce_enabled is True
        assert config.signature_verification_enabled is False
        assert config.require_message_signatures is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BotConfig(
            name="TestBot",
            announce=300,
            signature_verification_enabled=True,
            require_message_signatures=True,
            require_stamps=True,
            request_unknown_identities=True,
            stamp_cost=16,
        )
        assert config.name == "TestBot"
        assert config.announce == 300
        assert config.signature_verification_enabled is True
        assert config.require_message_signatures is True
        assert config.require_stamps is True
        assert config.request_unknown_identities is True
        assert config.stamp_cost == 16


class TestLXMFBot:
    """Test LXMFBot basic functionality."""

    def test_bot_initialization(self, test_bot):
        """Test bot initializes correctly."""
        assert test_bot.config.name == "TestBot"
        assert test_bot.commands is not None
        assert test_bot.cogs is not None
        assert test_bot.events is not None
        assert test_bot.permissions is not None

    def test_command_registration(self, test_bot):
        """Test command registration works."""

        @test_bot.command(name="test")
        def test_command(ctx):
            ctx.reply("Test response")

        assert "test" in test_bot.commands
        cmd = test_bot.commands["test"]
        assert cmd.name == "test"
        assert cmd.callback == test_command

    def test_admin_check(self, test_bot):
        """Test admin checking functionality."""
        test_sender = "test_hash_123"

        # Initially no admins
        assert not test_bot.is_admin(test_sender)

        # Add admin
        test_bot.admins.add(test_sender)
        assert test_bot.is_admin(test_sender)

        # Remove admin
        test_bot.admins.remove(test_sender)
        assert not test_bot.is_admin(test_sender)

    def test_bot_validation(self, test_bot):
        """Test bot validation functionality."""
        results = test_bot.validate()
        # Should return a string with validation results
        assert isinstance(results, str)
        assert len(results) > 0

    def test_name_property_aliases_config(self, test_bot):
        assert test_bot.name == test_bot.config.name
        test_bot.name = "RenamedBot"
        assert test_bot.config.name == "RenamedBot"
        assert test_bot.name == "RenamedBot"

    def test_effective_announce_display_name_file_priority(
        self,
        test_bot_config,
        test_config_dir,
    ):
        import uuid

        unique = test_config_dir / f"bot_name_{uuid.uuid4().hex[:8]}"
        unique.mkdir(exist_ok=True)
        config = test_bot_config.__dict__.copy()
        config["storage_path"] = str(unique / "storage")
        config["announce_display_name_file"] = "custom_title.txt"
        bot = LXMFBot(**config)
        bot.config_path = str(unique)

        (Path(bot.config_path) / BOT_DISPLAY_NAME_FILE).write_text(
            "FromFile\n",
            encoding="utf-8",
        )
        (Path(bot.config_path) / "custom_title.txt").write_text(
            "FromCustom\n",
            encoding="utf-8",
        )
        assert bot._effective_announce_display_name() == "FromCustom"

        bot.config.announce_display_name_file = None
        assert bot._effective_announce_display_name() == "FromFile"

        (Path(bot.config_path) / BOT_DISPLAY_NAME_FILE).unlink()
        assert bot._effective_announce_display_name() == bot.config.name

        bot.cleanup()


class TestCommandSystem:
    """Test command system functionality."""

    def test_command_creation(self):
        """Test Command class creation."""
        cmd = Command(
            name="test_cmd",
            description="A test command",
            admin_only=True,
        )

        assert cmd.name == "test_cmd"
        assert cmd.description == "A test command"
        assert cmd.admin_only is True
        assert cmd.permissions is not None

    def test_command_decorator(self):
        """Test command decorator functionality."""
        cmd = Command("ping", "Ping command")

        @cmd
        def ping_func(ctx):
            return "pong"

        assert cmd.callback == ping_func
        assert cmd.name == "ping"

    def test_command_descriptor(self, test_bot):
        """Test command descriptor functionality."""

        class TestCog:
            def __init__(self, bot):
                self.bot = bot

            @Command("cog_cmd", "Command from cog")
            def cog_command(self, ctx):
                ctx.reply("Cog response")

        cog = TestCog(test_bot)
        test_bot.add_cog(cog)

        assert "cog_cmd" in test_bot.commands
        cmd = test_bot.commands["cog_cmd"]
        assert cmd.name == "cog_cmd"
        # Just check that the callback exists and is callable
        assert callable(cmd.callback)


class TestSignatureSystem:
    """Test cryptographic signature system."""

    def test_signature_manager_creation(self, test_bot):
        """Test signature manager is created properly."""
        assert hasattr(test_bot, "signature_manager")
        assert test_bot.signature_manager is not None

    def test_signature_verification_disabled(self, test_bot):
        """Test signature verification when disabled."""
        # With verification disabled, should always return True
        assert test_bot.signature_manager.verification_enabled is False
        assert test_bot.signature_manager.should_verify_message("test") is False

    def test_signature_verification_enabled(self, test_config_dir):
        """Test signature verification when enabled."""
        import uuid

        unique_config_path = test_config_dir / f"secure_bot_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        # Create a unique identity for this test
        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        # Temporarily replace the identity loading
        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                name="SecureBot",
                signature_verification_enabled=True,
                permissions_enabled=True,  # Enable permissions for this test
                storage_path=str(unique_config_path / "storage"),
                test_mode=True,  # USE TEST MODE TO AVOID CRASH
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            assert bot.signature_manager.verification_enabled is True
            # Test with a non-admin user (should require verification)
            assert bot.signature_manager.should_verify_message("non_admin_user") is True

            bot.cleanup()
        finally:
            # Restore original function
            RNS.Identity.from_file = original_from_file


class TestEventSystem:
    """Test event system functionality."""

    def test_event_creation(self):
        """Test Event creation."""
        from lxmfy.events import Event

        event = Event("test_event", {"key": "value"})
        assert event.name == "test_event"
        assert event.data["key"] == "value"
        assert event.cancelled is False

    def test_event_cancellation(self):
        """Test event cancellation."""
        from lxmfy.events import Event

        event = Event("test_event")
        assert not event.cancelled

        event.cancel()
        assert event.cancelled

    def test_event_manager(self, test_bot):
        """Test event manager functionality."""
        events_fired = []

        @test_bot.events.on("test_event")
        def test_handler(event):
            events_fired.append(event.data)

        from lxmfy.events import Event

        test_event = Event("test_event", {"test": "data"})
        test_bot.events.dispatch(test_event)

        assert len(events_fired) == 1
        assert events_fired[0]["test"] == "data"


class TestStorageSystem:
    """Test storage system functionality."""

    def test_storage_initialization(self, test_bot):
        """Test storage is initialized correctly."""
        assert test_bot.storage is not None

    def test_storage_operations(self, test_bot):
        """Test basic storage operations."""
        # Test set/get
        test_bot.storage.set("test_key", {"data": "value"})
        result = test_bot.storage.get("test_key")
        assert result["data"] == "value"

        # Test exists
        assert test_bot.storage.exists("test_key")
        assert not test_bot.storage.exists("nonexistent_key")

        # Test scan
        test_bot.storage.set("test_prefix_1", "value1")
        test_bot.storage.set("test_prefix_2", "value2")
        test_bot.storage.set("other_key", "value3")

        results = test_bot.storage.scan("test_prefix_")
        assert len(results) == 2
        assert "test_prefix_1" in results
        assert "test_prefix_2" in results

        # Test delete
        test_bot.storage.delete("test_key")
        assert not test_bot.storage.exists("test_key")


class TestPermissionSystem:
    """Test permission system functionality."""

    def test_permission_manager_creation(self, test_bot):
        """Test permission manager is created."""
        assert test_bot.permissions is not None
        assert hasattr(test_bot.permissions, "enabled")
        assert not test_bot.permissions.enabled  # Disabled by default in tests

    def test_permission_check_disabled(self, test_bot):
        """Test permissions when system is disabled."""
        # When disabled, all permissions should be granted
        assert test_bot.permissions.has_permission("any_user", "any_perm")

    def test_role_creation(self, test_config_dir):
        """Test role creation and management."""
        import uuid

        from lxmfy.permissions import DefaultPerms

        unique_config_path = test_config_dir / f"perm_bot_{uuid.uuid4().hex[:8]}"
        unique_config_path.mkdir(exist_ok=True)

        # Create a unique identity for this test
        test_identity = RNS.Identity()
        identity_file = unique_config_path / "identity"
        test_identity.to_file(str(identity_file))

        # Temporarily replace the identity loading
        original_from_file = RNS.Identity.from_file
        RNS.Identity.from_file = lambda path: test_identity

        try:
            config = BotConfig(
                permissions_enabled=True,
                storage_path=str(unique_config_path / "storage"),
                test_mode=True,  # USE TEST MODE TO AVOID CRASH
            )
            bot = LXMFBot(**config.__dict__)
            bot.config_path = str(unique_config_path)

            # Create a custom role
            role = bot.permissions.create_role(
                "moderator",
                DefaultPerms.MANAGE_MESSAGES,
                description="Can manage messages",
            )

            assert role.name == "moderator"
            assert role.permissions == DefaultPerms.MANAGE_MESSAGES
            assert role.description == "Can manage messages"

            bot.cleanup()
        finally:
            # Restore original function
            RNS.Identity.from_file = original_from_file
