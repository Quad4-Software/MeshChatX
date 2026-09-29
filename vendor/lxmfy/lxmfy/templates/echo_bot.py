"""Simple echo bot template with cryptographic signature verification."""

from lxmfy import IconAppearance, LXMFBot, pack_icon_appearance_field


class EchoBot:
    """A simple echo bot that repeats messages with cryptographic signature verification."""

    def __init__(self, test_mode=False):
        """Initializes the EchoBot with signature verification enabled."""
        self.bot = LXMFBot(
            name="Echo Bot",
            announce=600,
            command_prefix="",
            first_message_enabled=True,
            test_mode=test_mode,
        )
        self.setup_commands()
        self.setup_message_handlers()

        # Define and pack the icon appearance for the bot
        icon_data = IconAppearance(
            icon_name="forum",
            fg_color=b"\xad\xd8\xe6",
            bg_color=b"\x3b\x59\x98",
        )  # Light blue on dark blue
        self.icon_lxmf_field = pack_icon_appearance_field(icon_data)

    def setup_message_handlers(self):
        """Sets up the bot's message handlers."""

        @self.bot.on_message()
        def echo_non_command_messages(sender, message):
            """Echoes back messages that are not commands."""
            content = message.content.decode("utf-8").strip()
            if not content:
                return False

            # Check if this would be processed as a command
            command_name = content.split()[0]
            if command_name in self.bot.commands:
                return False  # Let the command handler take care of it

            # Echo the message since it's not a command
            self.bot.send(
                sender,
                content,
                lxmf_fields=self.icon_lxmf_field,
            )
            return False  # Continue processing (though no commands will match)

    def setup_commands(self):
        """Sets up the bot's commands and event handlers."""

        @self.bot.command(name="echo", description="Echo back your message")
        def echo(ctx):
            """Echoes back the message provided by the user.

            Args:
                ctx: The command context.

            """
            if ctx.args:
                ctx.reply(" ".join(ctx.args), lxmf_fields=self.icon_lxmf_field)
            else:
                ctx.reply("Usage: echo <message>", lxmf_fields=self.icon_lxmf_field)

        @self.bot.on_first_message()
        def welcome(sender, message):
            """Greets the user on their first message and explains the bot's functionality.

            Args:
                sender: The sender of the message.
                message: The message received.

            Returns:
                True to indicate the message was handled.

            """
            content = message.content.decode("utf-8").strip()
            self.bot.send(
                sender,
                f"Hi! I'm an echo bot, You said: {content}\n\n"
                "Try: echo <message> to make me repeat things!",
                lxmf_fields=self.icon_lxmf_field,
            )
            return True

    def run(self):
        """Runs the bot."""
        self.bot.run()
