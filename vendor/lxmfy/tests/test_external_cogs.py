import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lxmfy import BotConfig, LXMFBot
from lxmfy.cogs_core import _get_sandbox_command, load_cogs_from_directory


@pytest.fixture
def external_cog_setup():
    """Set up a temporary directory with an external script cog."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        cogs_dir = temp_path / "cogs"
        cogs_dir.mkdir()

        # Create a simple bash script
        script_path = cogs_dir / "test_cmd.sh"
        script_content = """#!/bin/bash
echo "Hello from external script! Sender: $1 Content: $2"
"""
        script_path.write_text(script_content)

        # Make it executable
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)

        yield temp_path


def test_cog_external_loading(external_cog_setup):
    """Test that external script cogs are loaded correctly."""
    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=True,
        config_path=str(external_cog_setup),
        storage_path=str(external_cog_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(external_cog_setup)

    # Load cogs
    load_cogs_from_directory(bot)

    assert "test_cmd" in bot.commands
    cmd = bot.commands["test_cmd"]
    assert cmd.name == "test_cmd"
    assert cmd.threaded is True  # Should always be threaded
    assert "External script command" in cmd.description


def test_cog_external_execution(external_cog_setup):
    """Test that external script cogs execute and return output."""
    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=True,
        external_cogs_sandbox_enabled=False,
        config_path=str(external_cog_setup),
        storage_path=str(external_cog_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(external_cog_setup)

    # Load cogs
    load_cogs_from_directory(bot)

    cmd = bot.commands["test_cmd"]

    # Mock message
    msg = MagicMock()
    msg.sender = "test_sender"
    msg.content = "/test_cmd hello world"
    msg.args = ["hello", "world"]

    # Execute callback
    cmd.callback(msg)

    # Check if msg.reply was called with expected output
    msg.reply.assert_called_once()
    args, _ = msg.reply.call_args
    output = args[0]
    assert "Hello from external script!" in output
    assert "Sender: test_sender" in output
    assert "Content: /test_cmd hello world" in output


def test_cog_external_disabled(external_cog_setup):
    """Test that external script cogs are NOT loaded when disabled."""
    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=False,
        config_path=str(external_cog_setup),
        storage_path=str(external_cog_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(external_cog_setup)

    # Load cogs
    load_cogs_from_directory(bot)

    assert "test_cmd" not in bot.commands


def test_sandbox_detection_bwrap():
    """Test bubblewrap sandbox detection."""
    bot = MagicMock()
    bot.config.external_cogs_sandbox_enabled = True
    bot.config.external_cogs_sandbox_type = "auto"

    with (
        patch("shutil.which") as mock_which,
        patch("sys.platform", "linux"),
        patch("os.path.exists", return_value=True),
    ):
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x == "bwrap" else None

        cmd = _get_sandbox_command(bot, "/path/to/script")
        assert cmd is not None
        assert "/usr/bin/bwrap" in cmd


def test_sandbox_detection_firejail():
    """Test firejail sandbox detection."""
    bot = MagicMock()
    bot.config.external_cogs_sandbox_enabled = True
    bot.config.external_cogs_sandbox_type = "auto"

    with patch("shutil.which") as mock_which, patch("sys.platform", "linux"):
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x == "firejail" else None

        cmd = _get_sandbox_command(bot, "/path/to/script")
        assert cmd is not None
        assert "/usr/bin/firejail" in cmd


def test_cog_external_timeout_enforcement(external_cog_setup):
    """Test that external script cogs time out correctly."""
    # Create a script that sleeps forever
    cogs_dir = external_cog_setup / "cogs"
    timeout_script = cogs_dir / "timeout.sh"
    timeout_script.write_text("#!/bin/bash\nsleep 10")
    os.chmod(timeout_script, os.stat(timeout_script).st_mode | stat.S_IEXEC)

    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=True,
        external_cogs_sandbox_enabled=False,
        external_cogs_timeout=1,  # 1 second timeout
        config_path=str(external_cog_setup),
        storage_path=str(external_cog_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(external_cog_setup)

    load_cogs_from_directory(bot)
    cmd = bot.commands["timeout"]

    msg = MagicMock()
    cmd.callback(msg)

    msg.reply.assert_called_with("Error: Command timeout.sh timed out.")


def test_cog_external_timeout_disabled(external_cog_setup):
    """Test that external script cogs don't time out when timeout is 0."""
    # Create a script that sleeps for 2 seconds
    cogs_dir = external_cog_setup / "cogs"
    sleep_script = cogs_dir / "sleep.sh"
    sleep_script.write_text("#!/bin/bash\nsleep 1.5\necho 'Done sleeping'")
    os.chmod(sleep_script, os.stat(sleep_script).st_mode | stat.S_IEXEC)

    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=True,
        external_cogs_sandbox_enabled=False,
        external_cogs_timeout=0,  # Infinite timeout
        config_path=str(external_cog_setup),
        storage_path=str(external_cog_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(external_cog_setup)

    load_cogs_from_directory(bot)
    cmd = bot.commands["sleep"]

    msg = MagicMock()
    cmd.callback(msg)

    msg.reply.assert_called_with("Done sleeping")
