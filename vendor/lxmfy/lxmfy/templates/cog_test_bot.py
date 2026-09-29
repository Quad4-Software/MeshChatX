"""CogTest Bot Template - Tests cog command loading functionality.

This template demonstrates proper cog usage and serves as a test case
for the command loading system.
"""

from lxmfy import Command, LXMFBot
from lxmfy.commands import Cog


class TestCog(Cog):
    """Test cog with various command types to verify loading works correctly."""

    def __init__(self, bot):
        super().__init__(bot)

    @Command(name="cogtest", description="Test command from cog")
    def cog_test_command(self, msg):
        """Test basic cog command functionality."""
        msg.reply("✅ Cog command working correctly!")

    @Command(
        name="cogadmin",
        description="Admin test command from cog",
        admin_only=True,
    )
    def cog_admin_command(self, msg):
        """Test admin cog command functionality."""
        msg.reply("🔒 Admin cog command working correctly!")

    @Command(
        name="coghelp",
        description="Help command from cog using Command decorator",
    )
    def cog_help_command(self, msg):
        """Test Command decorator in cog."""
        msg.reply("""
🔧 CogTest Bot Commands:
/cogtest - Test basic cog command
/cogadmin - Test admin cog command (admin only)
/coghelp - This help message
/status - Bot status
        """)


class CogTestBot:
    """Template bot that uses cogs for testing command loading."""

    def __init__(self, name="CogTestBot", test_mode=False):
        self.bot = LXMFBot(
            name=name,
            announce=600,
            announce_immediately=True,
            admins=set(),
            hot_reloading=True,
            rate_limit=5,
            cooldown=60,
            max_warnings=3,
            warning_timeout=300,
            command_prefix="/",
            cogs_enabled=False,
            permissions_enabled=False,
            storage_type="json",
            storage_path="cogtest_data",
            first_message_enabled=True,
            test_mode=test_mode,
        )

        self.bot.add_cog(TestCog(self.bot))

        @self.bot.command(name="status", description="Show bot status")
        def status_command(msg):
            """Show bot status and loaded commands."""
            cog_commands = [
                cmd
                for cmd in self.bot.commands
                if cmd in ["cogtest", "cogadmin", "coghelp"]
            ]
            msg.reply(f"""
🤖 CogTest Bot Status:
- Commands loaded: {len(self.bot.commands)}
- Cog commands: {", ".join(cog_commands)}
- Cogs loaded: {len(self.bot.cogs)}
- Test status: {"✅ PASS" if len(cog_commands) == 3 else "❌ FAIL"}
            """)

    def run(self):
        """Run the bot."""
        self.bot.run()


def setup(bot):
    """Setup function for when used as a cog module."""
    bot.add_cog(TestCog(bot))
