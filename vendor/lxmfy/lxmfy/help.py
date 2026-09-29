"""Help command system for LXMFy."""

from dataclasses import dataclass

from .permissions import DefaultPerms


@dataclass
class HelpFormatter:
    """Default help formatter for commands."""

    @staticmethod
    def format_command(command) -> str:
        """Format a single command's help.

        Args:
            command: The command object to format.

        Returns:
            A formatted string containing the command's help information.

        """
        help_text = [
            f"**Command**: `{command.name}`",
            f"**Description**: {command.help.description}",
        ]

        if command.help.aliases:
            help_text.append(
                f"**Aliases**: {', '.join(f'`{a}`' for a in command.help.aliases)}",
            )

        if command.help.usage:
            help_text.append(f"**Usage**: `{command.help.usage}`")

        if command.help.examples:
            help_text.append("**Examples**:")
            help_text.extend(f"  - `{ex}`" for ex in command.help.examples)

        if command.permissions != DefaultPerms.USE_COMMANDS:
            perms = [
                perm.name
                for perm in DefaultPerms
                if (perm.value & command.permissions.value)
                and perm != DefaultPerms.NONE
            ]
            if perms:
                help_text.append("**Required Permissions**:")
                help_text.extend(f"  - {p}" for p in perms)

        if command.admin_only:
            help_text.append("*(Admin only)*")

        return "\n".join(help_text)

    @staticmethod
    def format_category(category: str, commands: list) -> str:
        """Format a category of commands.

        Args:
            category (str): The name of the category.
            commands (list): A list of command objects in the category.

        Returns:
            str: A formatted string containing the category's help information.

        """
        # Deduplicate commands (aliases point to same command)
        unique_cmds = {}
        for cmd in commands:
            unique_cmds[cmd.name] = cmd

        help_text = [f"\n**{category}**"]
        help_text.extend(
            f"  * `{cmd.name}`: {cmd.help.description}"
            for cmd in sorted(unique_cmds.values(), key=lambda x: x.name)
        )
        return "\n".join(help_text)

    @staticmethod
    def format_all_commands(categories: dict[str, list]) -> str:
        """Format the complete help listing.

        Args:
            categories (dict): A dictionary where keys are category names and values are lists of command objects.

        Returns:
            str: A formatted string containing help information for all commands.

        """
        help_text = ["**Bot Help Menu**", "Use `help <command>` for more details."]

        help_text.extend(
            HelpFormatter.format_category(category, categories[category])
            for category in sorted(categories.keys())
        )

        return "\n".join(help_text)


class HelpSystem:
    """A system for providing help information about available commands."""

    def __init__(self, bot, formatter=None):
        """Initialize the HelpSystem.

        Args:
            bot: The bot instance.
            formatter: An optional help formatter.  Defaults to HelpFormatter.

        """
        self.bot = bot
        self.formatter = formatter or HelpFormatter()

        @bot.command(name="help", description="Show help for commands")
        def help_command(ctx):
            """Handle the 'help' command.

            Args:
                ctx: The command context.

            """
            args = ctx.args
            if not args:
                categories = self._get_categorized_commands(ctx.is_admin)
                response = self.formatter.format_all_commands(categories)
                ctx.reply(response)
                return

            command_name = args[0]
            if command_name in self.bot.commands:
                command = self.bot.commands[command_name]
                if command.admin_only and not ctx.is_admin:
                    ctx.reply("This command is for administrators only.")
                    return
                response = self.formatter.format_command(command)
                ctx.reply(response)
                return
            ctx.reply(f"Command '{command_name}' not found.")
            return

    def _get_categorized_commands(self, is_admin: bool) -> dict[str, list]:
        """Group commands by category.

        Args:
            is_admin (bool): Whether the user is an admin.

        Returns:
            dict[str, list]: A dictionary where keys are category names and values are lists of command objects.

        """
        categories = {}

        for cmd in self.bot.commands.values():
            if cmd.admin_only and not is_admin:
                continue

            category = cmd.help.category or "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(cmd)

        return categories
