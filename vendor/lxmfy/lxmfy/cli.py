"""CLI module for LXMFy bot framework.

Provides an interactive and colorful command-line interface for creating and managing LXMF bots,
including bot file creation and example cog generation.
"""

import argparse
import os
import re
import sys

from .__version__ import __version__
from .colors import (
    Colors,
    init_colors,
    print_error,
    print_header,
    print_info,
    print_menu,
    print_success,
    print_warning,
)
from .templates import CogTestBot, EchoBot, NoteBot, ReminderBot


def get_user_choice() -> str:
    """Get user's choice from the menu."""
    while True:
        if Colors.is_colors_supported():
            choice = input(f"{Colors.CYAN}Enter your choice (1-3): {Colors.ENDC}")
        else:
            choice = input("Enter your choice (1-3): ")
        if choice in ["1", "2", "3"]:
            return choice
        print_error("Invalid choice. Please enter a number between 1 and 3.")


def get_bot_name() -> str:
    """Get bot name from user input."""
    while True:
        if Colors.is_colors_supported():
            name = input(f"{Colors.CYAN}Enter bot name: {Colors.ENDC}")
        else:
            name = input("Enter bot name: ")
        try:
            return validate_bot_name(name)
        except ValueError as ve:
            print_error(f"Invalid bot name: {ve}")


def get_template_choice() -> str:
    """Get template choice from user input."""
    templates = ["basic", "echo", "reminder", "note", "cogtest"]
    if Colors.is_colors_supported():
        print(f"\n{Colors.CYAN}Available templates:{Colors.ENDC}")
        for i, template in enumerate(templates, 1):
            print(f"{Colors.BOLD}{i}.{Colors.ENDC} {template}")
    else:
        print("\nAvailable templates:")
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template}")

    while True:
        if Colors.is_colors_supported():
            choice = input(f"\n{Colors.CYAN}Select template (1-5): {Colors.ENDC}")
        else:
            choice = input("\nSelect template (1-5): ")
        if choice in ["1", "2", "3", "4", "5"]:
            return templates[int(choice) - 1]
        print_error("Invalid choice. Please enter a number between 1 and 5.")


def interactive_create() -> None:
    """Interactive bot creation process."""
    print_header("Create New Bot")
    bot_name = get_bot_name()
    template = get_template_choice()

    if Colors.is_colors_supported():
        output_path = (
            input(
                f"{Colors.CYAN}Enter output path (default: {bot_name}.py): {Colors.ENDC}",
            )
            or f"{bot_name}.py"
        )
    else:
        output_path = (
            input(f"Enter output path (default: {bot_name}.py): ") or f"{bot_name}.py"
        )

    try:
        bot_path = create_from_template(template, output_path, bot_name)
        if template == "basic":
            create_example_cog(bot_path)
            print_success("Bot created successfully!")
            print_info(f"""
Files created:
  - {bot_path} (main bot file)
  - {os.path.join(os.path.dirname(bot_path), "cogs")}
    - __init__.py
    - basic.py (example cog)

To start your bot:
  python {bot_path}

To add admin rights, edit {bot_path} and add your LXMF hash to the admins list.
            """)
        else:
            print_success("Bot created successfully!")
            print_info(f"""
Files created:
  - {bot_path} (main bot file)

To start your bot:
  python {bot_path}

To add admin rights, edit {bot_path} and add your LXMF hash to the admins list.
            """)
    except Exception as e:
        print_error(f"Error creating bot: {e!s}")


def interactive_run() -> None:
    """Interactive bot running process."""
    print_header("Run Template Bot")
    template = get_template_choice()

    if Colors.is_colors_supported():
        custom_name = input(f"{Colors.CYAN}Enter custom name (optional): {Colors.ENDC}")
    else:
        custom_name = input("Enter custom name (optional): ")
    if custom_name:
        try:
            custom_name = validate_bot_name(custom_name)
        except ValueError as ve:
            print_warning(f"Invalid custom name provided. Using default. ({ve})")
            custom_name = None

    try:
        template_map = {
            "echo": EchoBot,
            "reminder": ReminderBot,
            "note": NoteBot,
            "cogtest": CogTestBot,
        }

        BotClass = template_map[template]
        print_header(f"Starting {template} Bot")
        bot_instance = BotClass()

        if custom_name:
            if hasattr(bot_instance, "bot"):
                bot_instance.bot.config.name = custom_name
                bot_instance.bot.name = custom_name
            else:
                bot_instance.config.name = custom_name
                bot_instance.name = custom_name
            print_info(f"Running with custom name: {custom_name}")

        bot_instance.run()
    except Exception as e:
        print_error(f"Error running template bot: {e!s}")


def interactive_mode() -> None:
    """Run the CLI in interactive mode."""
    while True:
        print_menu()
        choice = get_user_choice()

        if choice == "1":
            interactive_create()
        elif choice == "2":
            interactive_run()
        elif choice == "3":
            print_success("Goodbye!")
            sys.exit(0)

        if Colors.is_colors_supported():
            input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
        else:
            input("\nPress Enter to continue...")


def sanitize_filename(filename: str) -> str:
    """Sanitizes the filename while preserving the extension.

    Args:
        filename: The filename to sanitize.

    Returns:
        Sanitized filename with proper extension.

    """
    base, ext = os.path.splitext(os.path.basename(filename))
    base = re.sub(r"[^a-zA-Z0-9\-_]", "", base)

    if not ext or ext != ".py":
        ext = ".py"

    return f"{base}{ext}"


def validate_bot_name(name: str) -> str:
    """Validates and sanitizes a bot name.

    Args:
        name: The proposed bot name.

    Returns:
        The sanitized bot name.

    Raises:
        ValueError: If the name is invalid.

    """
    if not name:
        raise ValueError("Bot name cannot be empty")

    sanitized = "".join(c for c in name if c.isalnum() or c in " -_")
    if not sanitized:
        raise ValueError("Bot name must contain valid characters")

    return sanitized


def create_bot_file(name: str, output_path: str, no_cogs: bool = False) -> str:
    """Creates a new bot file from a template.

    Args:
        name: The name for the bot.
        output_path: The desired output path.
        no_cogs: Whether to disable cogs loading.

    Returns:
        The path to the created bot file.

    Raises:
        RuntimeError: If file creation fails.

    """
    try:
        name = validate_bot_name(name)

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if output_path.endswith("/") or output_path.endswith("\\"):
            base_name = "bot.py"
            output_path = os.path.join(output_path, base_name)
        elif not output_path.endswith(".py"):
            output_path += ".py"

        safe_path = os.path.abspath(output_path)

        template = f"""from lxmfy import LXMFBot

bot = LXMFBot(
    name="{name}",
    announce=600,
    announce_immediately=True,
    admins=set(),
    hot_reloading=False,
    rate_limit=5,
    cooldown=60,
    max_warnings=3,
    warning_timeout=300,
    command_prefix="/",
    cogs_dir="cogs",
    cogs_enabled={not no_cogs},
    permissions_enabled=False,
    storage_type="json",
    storage_path="data",
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,
    announce_enabled=True
)

if __name__ == "__main__":
    bot.run()
"""
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(template)

        return os.path.relpath(safe_path)

    except Exception as e:
        raise RuntimeError(f"Failed to create bot file: {e!s}") from e


def create_example_cog(bot_path: str) -> None:
    """Creates an example cog and the necessary directory structure.

    Args:
        bot_path: The path to the bot file to determine the cogs location.

    """
    try:
        bot_dir = os.path.dirname(os.path.abspath(bot_path))
        cogs_dir = os.path.join(bot_dir, "cogs")
        os.makedirs(cogs_dir, exist_ok=True)

        init_path = os.path.join(cogs_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write("")

        template = """from lxmfy import Command

class BasicCommands:
    def __init__(self, bot):
        self.bot = bot

    @Command(name="hello", description="Says hello")
    async def hello(self, ctx):
        ctx.reply(f"Hello {ctx.sender}!")

    @Command(name="about", description="About this bot")
    async def about(self, ctx):
        ctx.reply("I'm a bot created with LXMFy!")

def setup(bot):
    bot.add_cog(BasicCommands(bot))
"""
        basic_path = os.path.join(cogs_dir, "basic.py")
        with open(basic_path, "w", encoding="utf-8") as f:
            f.write(template)

    except Exception as e:
        raise RuntimeError(f"Failed to create example cog: {e!s}") from e


def create_from_template(template_name: str, output_path: str, bot_name: str) -> str:
    """Creates a bot from a template.

    Args:
        template_name: The name of the template to use.
        output_path: The desired output path.
        bot_name: The name for the bot.

    Returns:
        The path to the created bot file.

    Raises:
        ValueError: If the template is invalid.

    """
    try:
        name = validate_bot_name(bot_name)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        if output_path.endswith("/") or output_path.endswith("\\"):
            base_name = "bot.py"
            output_path = os.path.join(output_path, base_name)
        elif not output_path.endswith(".py"):
            output_path += ".py"

        safe_path = os.path.abspath(output_path)

        if template_name == "basic":
            return create_bot_file(name, safe_path)

        template_map = {
            "echo": EchoBot,
            "reminder": ReminderBot,
            "note": NoteBot,
            "cogtest": CogTestBot,
        }

        if template_name not in template_map:
            raise ValueError(
                f"Invalid template: {template_name}. Available templates: basic, {', '.join(template_map.keys())}",
            )

        template = f"""from lxmfy.templates import {template_map[template_name].__name__}

if __name__ == "__main__":
    bot = {template_map[template_name].__name__}()
    bot.bot.name = "{name}"  # Set custom name
    bot.run()
"""
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(template)

        return os.path.relpath(safe_path)

    except Exception as e:
        raise RuntimeError(f"Failed to create bot from template: {e!s}") from e


def is_safe_path(path: str, base_path: str = None) -> bool:
    """Checks if a path is safe and within the allowed directory.

    Args:
        path: The path to check.
        base_path: The base path to check against. If None, all paths are considered safe.

    Returns:
        True if the path is safe, False otherwise.

    """
    try:
        if base_path:
            base_path = os.path.abspath(base_path)
            path = os.path.abspath(path)
            return path.startswith(base_path)
        return True
    except Exception:
        return False


def main() -> None:
    """Main CLI entry point."""
    try:
        init_colors()

        if len(sys.argv) == 1:
            interactive_mode()
            return

        print_header("LXMFy Bot Framework")

        parser = argparse.ArgumentParser(
            description=f"LXMFy Bot Tool (version {__version__})",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  lxmfy create                          # Create basic bot file 'bot.py'
  lxmfy create mybot                    # Create basic bot file 'mybot.py'
  lxmfy create --template echo mybot    # Create echo bot file 'mybot.py'
  lxmfy create --template reminder bot  # Create reminder bot file 'bot.py'
  lxmfy create --template note notes    # Create note-taking bot file 'notes.py'
  lxmfy create --template cogtest test  # Create cog test bot file 'test.py'

  lxmfy run echo                        # Run the built-in echo bot
  lxmfy run reminder --name "MyReminder"  # Run the reminder bot with a custom name
  lxmfy run note                        # Run the built-in note bot
  lxmfy run cogtest                     # Run the cog test bot

  lxmfy signatures test                 # Test signature functionality
  lxmfy signatures enable               # Show how to enable signatures
  lxmfy signatures disable              # Show how to disable signatures
            """,
        )

        parser.add_argument(
            "command",
            choices=["create", "run", "signatures"],
            help="Create a bot file, run a template bot, or manage signatures",
        )
        parser.add_argument(
            "name",
            nargs="?",
            default=None,
            help="Name for 'create' (bot name/path) or 'run' (template name: echo, reminder, note)",
        )
        parser.add_argument(
            "directory",
            nargs="?",
            default=None,
            help="Output directory for 'create' command (optional)",
        )
        parser.add_argument(
            "--template",
            choices=["basic", "echo", "reminder", "note", "cogtest"],
            default="basic",
            help="Bot template to use for 'create' command (default: basic)",
        )
        parser.add_argument(
            "--name",
            dest="name_opt",
            default=None,
            help="Optional custom name for the bot (used with 'create' or 'run')",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Output file path or directory for 'create' command",
        )
        parser.add_argument(
            "--no-cogs",
            action="store_true",
            help="Disable cogs loading for 'create' command",
        )

        args = parser.parse_args()

        if args.command == "create":
            try:
                bot_name = args.name_opt or args.name or "MyLXMFBot"

                if args.output:
                    output_path = args.output
                elif args.directory:
                    output_path = os.path.join(args.directory, "bot.py")
                elif args.name:
                    if "." in args.name:
                        output_path = args.name
                        if not args.name_opt:
                            bot_name = os.path.splitext(os.path.basename(args.name))[0]
                    else:
                        output_path = f"{args.name}.py"
                else:
                    output_path = "bot.py"

                try:
                    bot_name = validate_bot_name(bot_name)
                except ValueError as ve:
                    print_error(f"Invalid bot name '{bot_name}'. {ve}")
                    sys.exit(1)

                print_header("Creating New Bot")
                bot_path = create_from_template(args.template, output_path, bot_name)

                if args.template == "basic":
                    create_example_cog(bot_path)
                    print_success("Bot created successfully!")
                    print_info(f"""
Files created:
  - {bot_path} (main bot file)
  - {os.path.join(os.path.dirname(bot_path), "cogs")}
    - __init__.py
    - basic.py (example cog)

To start your bot:
  python {bot_path}

To add admin rights, edit {bot_path} and add your LXMF hash to the admins list.
                    """)
                else:
                    print_success("Bot created successfully!")
                    print_info(f"""
Files created:
  - {bot_path} (main bot file)

To start your bot:
  python {bot_path}

To add admin rights, edit {bot_path} and add your LXMF hash to the admins list.
                    """)
            except Exception as e:
                print_error(f"Error creating bot: {e!s}")
                sys.exit(1)

        elif args.command == "run":
            template_name = args.name
            if not template_name:
                print_error(
                    "Please specify a template name to run (echo, reminder, note, cogtest)",
                )
                sys.exit(1)

            template_map = {
                "echo": EchoBot,
                "reminder": ReminderBot,
                "note": NoteBot,
                "cogtest": CogTestBot,
            }

            if template_name not in template_map:
                print_error(
                    f"Invalid template name '{template_name}'. Choose from: {', '.join(template_map.keys())}",
                )
                sys.exit(1)

            try:
                BotClass = template_map[template_name]
                print_header(f"Starting {template_name} Bot")
                bot_instance = BotClass()

                custom_name = args.name_opt
                if custom_name:
                    try:
                        validated_name = validate_bot_name(custom_name)
                        if hasattr(bot_instance, "bot"):
                            bot_instance.bot.config.name = validated_name
                            bot_instance.bot.name = validated_name
                        else:
                            bot_instance.config.name = validated_name
                            bot_instance.name = validated_name
                        print_info(f"Running with custom name: {validated_name}")
                    except ValueError as ve:
                        print_warning(
                            f"Invalid custom name '{custom_name}' provided. Using default. ({ve})",
                        )

                bot_instance.run()

            except Exception as e:
                print_error(f"Error running template bot '{template_name}': {e!s}")
                sys.exit(1)

        elif args.command == "signatures":
            try:
                print_header("Signature Management")
                if not args.name:
                    print_error("Please specify a subcommand: test, enable, disable")
                    print_info("Usage: lxmfy signatures <subcommand>")
                    print_info(
                        "  test     - Test signature verification with sample data",
                    )
                    print_info("  enable   - Show how to enable signature verification")
                    print_info(
                        "  disable  - Show how to disable signature verification",
                    )
                    sys.exit(1)

                subcommand = args.name

                if subcommand == "test":
                    print_info("Testing signature functionality...")
                    try:
                        import RNS

                        from lxmfy.signatures import FIELD_SIGNATURE, SignatureManager

                        identity1 = RNS.Identity()
                        identity2 = RNS.Identity()

                        class MockBot:
                            def __init__(self):
                                self.permissions = MockPermissions()

                        class MockPermissions:
                            @staticmethod
                            def has_permission(user, perm):
                                return False  # No bypass for testing

                        bot = MockBot()
                        sig_manager = SignatureManager(
                            bot,
                            verification_enabled=True,
                            require_signatures=False,
                        )

                        class MockMessage:
                            def __init__(
                                self,
                                source_hash,
                                dest_hash,
                                content,
                                title=None,
                                fields=None,
                            ):
                                self.source_hash = source_hash
                                self.destination_hash = dest_hash
                                self.content = content
                                self.title = title or b"Test"
                                self.fields = fields or {}

                        test_msg = MockMessage(
                            identity1.hash,
                            identity2.hash,
                            b"Hello, World!",
                            b"Test Message",
                        )

                        signature = sig_manager.sign_message(test_msg, identity1)
                        print_success(
                            f"OK Message signed successfully (signature length: {len(signature)} bytes)",
                        )

                        test_msg.fields[FIELD_SIGNATURE] = signature
                        is_valid = sig_manager.verify_message_signature(
                            test_msg,
                            signature,
                            RNS.hexrep(identity1.hash, delimit=False),
                        )
                        if is_valid:
                            print_success("OK Signature verification successful")
                        else:
                            print_error("FAIL Signature verification failed")

                        print_info("Signature test completed successfully!")

                    except Exception as e:
                        print_error(f"Signature test failed: {e!s}")
                        print_info("This may be due to RNS initialization requirements")
                        sys.exit(1)

                elif subcommand == "enable":
                    print_info(
                        "To enable signature verification in your bot, add these parameters to your LXMFBot constructor:",
                    )
                    print()
                    print(
                        "signature_verification_enabled=True,   # Enable signature checking",
                    )
                    print(
                        "require_message_signatures=False,      # Set to True to reject unsigned messages",
                        "require_stamps=False,                  # Set to True to reject invalid stamps",
                        "request_unknown_identities=False,      # Set to True to request unknown keys",
                    )
                    print()
                    print_info("Example:")
                    print("bot = LXMFBot(")
                    print("    name='MyBot',")
                    print("    signature_verification_enabled=True,")
                    print("    require_message_signatures=False,")
                    print("    require_stamps=False")
                    print(")")

                elif subcommand == "disable":
                    print_info(
                        "Signature verification is disabled by default. To explicitly disable:",
                    )
                    print()
                    print(
                        "signature_verification_enabled=False,  # Disable signature checking",
                    )
                    print(
                        "require_message_signatures=False,      # Not required when disabled",
                        "require_stamps=False,                  # Set to True to still require stamps",
                    )
                    print()
                    print_info(
                        "Or simply omit these parameters (they default to False)",
                    )

                else:
                    print_error(f"Unknown subcommand: {subcommand}")
                    print_info("Available subcommands: test, enable, disable")

            except Exception as e:
                print_error(f"Error in signatures command: {e!s}")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
