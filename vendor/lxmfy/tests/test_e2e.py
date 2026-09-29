"""End-to-end tests for LXMFy CLI and full bot functionality."""

import subprocess
import tempfile
import time
from pathlib import Path

from lxmfy import BotConfig, LXMFBot


class TestCLIE2E:
    """End-to-end tests for CLI functionality."""

    def test_cli_create_basic_bot(self, test_config_dir):
        """Test CLI bot creation."""
        import sys

        with tempfile.TemporaryDirectory() as temp_dir:
            bot_path = Path(temp_dir) / "test_bot.py"

            # Run CLI create command
            import os

            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path.cwd())

            cmd = [
                sys.executable,
                "-m",
                "lxmfy.cli",
                "create",
                "testbot",
                "--output",
                str(bot_path),
            ]

            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                cwd=test_config_dir,
                env=env,
            )

            assert result.returncode == 0
            assert "Bot created successfully" in result.stdout
            assert bot_path.exists()

            # Verify bot file content
            with open(bot_path) as f:
                content = f.read()

            assert "LXMFBot" in content
            assert "testbot" in content

    def test_cli_run_echo_bot(self, test_config_dir):
        """Test CLI running echo bot template."""
        # This test would start a bot process, but for CI we just verify
        # the command doesn't fail immediately
        import os
        import sys

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())

        cmd = [
            sys.executable,
            "-m",
            "lxmfy.cli",
            "run",
            "echo",
            "--name",
            "TestEchoBot",
        ]

        # Start the bot in a subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_config_dir,
            text=True,
            env=env,
        )

        # Let it run for a few seconds
        time.sleep(3)

        # Terminate the process
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        if process.returncode != 0 and process.returncode != -15:
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")

        # Should have started without immediate errors
        assert process.returncode == 0 or process.returncode == -15  # SIGTERM

    def test_cli_signatures_test(self, test_config_dir):
        """Test CLI signatures functionality."""
        import os
        import sys

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())

        cmd = [
            sys.executable,
            "-m",
            "lxmfy.cli",
            "signatures",
            "test",
        ]

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            cwd=test_config_dir,
            env=env,
        )

        # Should complete successfully
        assert result.returncode == 0
        assert "signature test" in result.stdout.lower()

    def test_cli_signatures_enable_disable(self, test_config_dir):
        """Test CLI signatures enable/disable instructions."""
        import os
        import sys

        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())

        # Test enable command
        cmd_enable = [
            sys.executable,
            "-m",
            "lxmfy.cli",
            "signatures",
            "enable",
        ]

        result = subprocess.run(
            cmd_enable,
            check=False,
            capture_output=True,
            text=True,
            cwd=test_config_dir,
            env=env,
        )

        assert result.returncode == 0
        assert "signature_verification_enabled=True" in result.stdout

        # Test disable command
        cmd_disable = [
            "python",
            "-m",
            "lxmfy.cli",
            "signatures",
            "disable",
        ]

        result = subprocess.run(
            cmd_disable,
            check=False,
            capture_output=True,
            text=True,
            cwd=test_config_dir,
            env=env,
        )

        assert result.returncode == 0
        assert "signature_verification_enabled=False" in result.stdout


class TestFullBotLifecycle:
    """Test complete bot lifecycle from creation to operation."""

    def test_bot_creation_and_startup(self, test_config_dir):
        """Test creating and starting a bot."""
        config = BotConfig(
            name="LifecycleTestBot",
            announce=0,  # Disable announcing
            announce_enabled=False,
            storage_path=str(test_config_dir / "lifecycle_storage"),
            cogs_enabled=False,
            permissions_enabled=False,
            test_mode=True,
        )

        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(test_config_dir)

        assert bot.config.name == "LifecycleTestBot"
        assert bot.router is None  # Should be None in test mode
        assert bot.local is None  # Should be None in test mode

        # Test cleanup
        bot.cleanup()

    def test_bot_with_commands(self, test_config_dir):
        """Test bot with custom commands."""
        config = BotConfig(
            name="CommandTestBot",
            announce_enabled=False,
            storage_path=str(test_config_dir / "command_storage"),
            cogs_enabled=False,
            test_mode=True,
        )

        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(test_config_dir)

        # Add test commands
        @bot.command("hello")
        def hello_cmd(ctx):
            ctx.reply("Hello from test bot!")

        @bot.command("echo", admin_only=True)
        def echo_cmd(ctx, message: str):
            ctx.reply(message)

        assert "hello" in bot.commands
        assert "echo" in bot.commands

        # Test command properties
        echo_cmd_obj = bot.commands["echo"]
        assert echo_cmd_obj.admin_only is True

        bot.cleanup()

    def test_bot_with_cogs(self, test_config_dir):
        """Test bot with cog extensions."""
        config = BotConfig(
            name="CogTestBot",
            announce_enabled=False,
            storage_path=str(test_config_dir / "cog_storage"),
            cogs_enabled=True,
            cogs_dir=str(test_config_dir / "test_cogs"),
            test_mode=True,
        )

        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(test_config_dir)

        # Create test cog
        cogs_dir = Path(test_config_dir) / "cogs"
        cogs_dir.mkdir(exist_ok=True)

        init_file = cogs_dir / "__init__.py"
        init_file.write_text("")

        cog_file = cogs_dir / "test_cog.py"
        cog_file.write_text("""
from lxmfy import Command

class TestCog:
    def __init__(self, bot):
        self.bot = bot

    @Command("cog_hello", "Hello from cog")
    def cog_hello(self, ctx):
        ctx.reply("Hello from cog!")

def setup(bot):
    bot.add_cog(TestCog(bot))
""")

        # Load cogs
        from lxmfy import load_cogs_from_directory

        load_cogs_from_directory(bot, "cogs")

        assert "cog_hello" in bot.commands

        bot.cleanup()

    def test_bot_with_signatures(self, test_config_dir):
        """Test bot with cryptographic signature verification."""
        config = BotConfig(
            name="SecureBot",
            announce_enabled=False,
            storage_path=str(test_config_dir / "secure_storage"),
            signature_verification_enabled=True,
            require_message_signatures=False,
            test_mode=True,
        )

        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(test_config_dir)

        assert bot.signature_manager.verification_enabled is True
        assert bot.signature_manager.require_signatures is False

        # Test signature manager functionality
        assert bot.signature_manager.should_verify_message("test_user") is True

        bot.cleanup()

    def test_bot_with_permissions(self, test_config_dir):
        """Test bot with permission system enabled."""
        config = BotConfig(
            name="PermBot",
            announce_enabled=False,
            storage_path=str(test_config_dir / "perm_storage"),
            permissions_enabled=True,
            test_mode=True,
        )

        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(test_config_dir)

        assert bot.permissions.enabled is True

        from lxmfy.permissions import DefaultPerms

        # Test role creation
        role = bot.permissions.create_role(
            "moderator",
            DefaultPerms.MANAGE_MESSAGES,
        )
        assert role.name == "moderator"

        # Test user permission assignment
        bot.permissions.assign_role("test_user", "moderator")
        assert bot.permissions.has_permission("test_user", DefaultPerms.MANAGE_MESSAGES)

        bot.cleanup()


class TestTemplateBotOperations:
    """Test that template bots can perform basic operations."""

    def test_echo_bot_operations(self, test_config_dir):
        """Test echo bot can handle commands."""
        from lxmfy.templates import EchoBot

        echo_bot = EchoBot(test_mode=True)

        # Verify commands are registered
        assert "echo" in echo_bot.bot.commands

        # Mock a context for testing
        class MockContext:
            def __init__(self):
                self.args = ["Hello", "World"]
                self.content = "/echo Hello World"
                self.sender = "test_sender"

            def reply(self, message, **kwargs):
                self.response = message

        ctx = MockContext()

        # Execute echo command
        echo_cmd = echo_bot.bot.commands["echo"]
        echo_cmd.callback(ctx)

        # Verify response
        assert hasattr(ctx, "response")
        assert "Hello World" in ctx.response

        echo_bot.bot.cleanup()

    def test_note_bot_operations(self, test_config_dir):
        """Test note bot can store and retrieve notes."""
        from lxmfy.templates import NoteBot

        note_bot = NoteBot(test_mode=True)

        # Mock context for testing
        class MockContext:
            def __init__(self, sender="test_user"):
                self.sender = sender
                self.args = []

            def reply(self, message):
                self.responses = getattr(self, "responses", [])
                self.responses.append(message)

        # Test note saving
        save_ctx = MockContext()
        save_ctx.args = ["This", "is", "a", "test", "note"]
        save_ctx.content = "/note This is a test note"

        note_cmd = note_bot.bot.commands["note"]
        note_cmd.callback(save_ctx)

        assert len(save_ctx.responses) == 1
        assert "saved" in save_ctx.responses[0].lower()

        # Test note listing
        list_ctx = MockContext()
        list_cmd = note_bot.bot.commands["notes"]
        list_cmd.callback(list_ctx)

        assert len(list_ctx.responses) == 1
        assert "test note" in list_ctx.responses[0]

        note_bot.bot.cleanup()

    def test_reminder_bot_operations(self, test_config_dir):
        """Test reminder bot can set and list reminders."""
        from lxmfy.templates import ReminderBot

        reminder_bot = ReminderBot(test_mode=True)

        class MockContext:
            def __init__(self, sender="test_user"):
                self.sender = sender
                self.args = []

            def reply(self, message):
                self.responses = getattr(self, "responses", [])
                self.responses.append(message)

        # Test reminder setting
        remind_ctx = MockContext()
        remind_ctx.args = ["1h", "Test", "reminder"]
        remind_ctx.content = "/remind 1h Test reminder"

        remind_cmd = reminder_bot.bot.commands["remind"]
        remind_cmd.callback(remind_ctx)

        assert len(remind_ctx.responses) == 1
        assert "remind" in remind_ctx.responses[0].lower()

        # Test reminder listing
        list_ctx = MockContext()
        list_cmd = reminder_bot.bot.commands["list"]
        list_cmd.callback(list_ctx)

        assert len(list_ctx.responses) == 1
        assert "reminders" in list_ctx.responses[0].lower()

        reminder_bot.bot.cleanup()
