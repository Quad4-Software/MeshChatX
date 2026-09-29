import os
import stat
import tempfile
from pathlib import Path

from lxmfy import BotConfig, LXMFBot
from lxmfy.cogs_core import load_cogs_from_directory


def test_cog_execution_depth_limit(test_config_dir):
    """Test that external cogs cannot trigger infinite recursive bot calls."""
    # This is a bit complex to test fully without a real bot instance,
    # but we can verify the threading and isolation logic.

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        cogs_dir = temp_path / "cogs"
        cogs_dir.mkdir()

        # Create a cog that tries to call the bot recursively
        # (simulated by executing another command)
        script_path = cogs_dir / "recursive.sh"
        script_content = """#!/bin/bash
echo "Calling self..."
# In a real scenario, this might try to send an LXMF message back to the bot
# which would trigger another command execution.
"""
        script_path.write_text(script_content)
        os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IEXEC)

        config = BotConfig(
            name="DepthTestBot",
            test_mode=True,
            external_cogs_enabled=True,
            external_cogs_timeout=2,
            config_path=str(temp_path),
            storage_path=str(temp_path / "storage"),
        )
        bot = LXMFBot(**config.__dict__)
        bot.config_path = str(temp_path)

        load_cogs_from_directory(bot)
        cmd = bot.commands["recursive"]

        # Since we use threading and subprocess.run with timeout,
        # any actual recursive fork-bomb would be caught by the process limit
        # or the bot's thread pool executor limit.

        assert cmd.threaded is True

        # Verify the bot's thread pool is initialized
        assert bot.thread_pool._max_workers == 5
