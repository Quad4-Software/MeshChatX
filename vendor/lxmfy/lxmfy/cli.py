"""CLI module for LXMFy bot framework.

Provides an interactive and colorful command-line interface for creating and managing LXMF bots,
including bot file creation and example cog generation.
"""

import argparse
import json
import os
import re
import sys
from typing import Any

from .__version__ import __version__
from .colors import (
    Colors,
    init_colors,
    print_check,
    print_error,
    print_header,
    print_info,
    print_kv,
    print_menu,
    print_section,
    print_success,
    print_warning,
)
from .templates import CogTestBot, EchoBot, NoteBot, ReminderBot, RRCBot


def get_user_choice() -> str:
    """Get user's choice from the menu."""
    while True:
        if Colors.is_colors_supported():
            choice = input(f"{Colors.CYAN}Enter your choice (1-4): {Colors.ENDC}")
        else:
            choice = input("Enter your choice (1-4): ")
        if choice in ["1", "2", "3", "4"]:
            return choice
        print_error("Invalid choice. Please enter a number between 1 and 4.")


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
    templates = ["basic", "echo", "reminder", "note", "cogtest", "rrc"]
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
            choice = input(f"\n{Colors.CYAN}Select template (1-6): {Colors.ENDC}")
        else:
            choice = input("\nSelect template (1-6): ")
        if choice in ["1", "2", "3", "4", "5", "6"]:
            return templates[int(choice) - 1]
        print_error("Invalid choice. Please enter a number between 1 and 6.")


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
        _print_created(bot_path, with_cogs=template == "basic")
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
            "rrc": RRCBot,
        }

        BotClass = template_map[template]
        print_header(f"Starting {template} Bot")

        if custom_name:
            try:
                bot_instance = BotClass(name=custom_name)
            except TypeError:
                bot_instance = BotClass()
                bot_instance.bot.config.name = custom_name
            print_info(f"Running with custom name: {custom_name}")
        else:
            bot_instance = BotClass()

        bot_instance.run()
    except Exception as e:
        print_error(f"Error running template bot: {e!s}")


def interactive_debug() -> None:
    """Interactive debugger."""
    print_header("Debugger")
    if Colors.is_colors_supported():
        config = (
            input(
                f"{Colors.CYAN}Bot config path (default: ./config): {Colors.ENDC}",
            ).strip()
            or None
        )
        dest = (
            input(
                f"{Colors.CYAN}Destination hash to probe (optional): {Colors.ENDC}",
            ).strip()
            or None
        )
    else:
        config = input("Bot config path (default: ./config): ").strip() or None
        dest = input("Destination hash to probe (optional): ").strip() or None

    from .debugger import Debugger

    dbg = Debugger(config_path=config)
    report = dbg.run_doctor(
        destination=dest,
        request_path=bool(dest),
        wait=15.0 if dest else 0.0,
    )
    dbg.print_report(report)
    out = dbg.save_report(report)
    print_success(f"Report saved to {out}")
    print_info("Share that file when asking for help (privacy-redacted).")


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
            interactive_debug()
        elif choice == "4":
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

        cogs_line = (
            "" if no_cogs else "\n# Drop .py files in ./cogs to add more commands."
        )

        template = f'''from lxmfy import LXMFBot
{cogs_line}
bot = LXMFBot("{name}", cogs_enabled={not no_cogs})


@bot.command("hello", description="Say hello")
def hello(ctx):
    ctx.reply(f"Hello {{ctx.sender}}!")


if __name__ == "__main__":
    bot.run()
'''

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
    def hello(self, ctx):
        ctx.reply(f"Hello {ctx.sender}!")

    @Command(name="about", description="About this bot")
    def about(self, ctx):
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
            "rrc": RRCBot,
        }

        if template_name not in template_map:
            raise ValueError(
                f"Invalid template: {template_name}. Available templates: basic, {', '.join(template_map.keys())}",
            )

        template = f"""from lxmfy.templates import {template_map[template_name].__name__}

if __name__ == "__main__":
    bot = {template_map[template_name].__name__}(name="{name}")
    bot.run()
"""
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(template)

        return os.path.relpath(safe_path)

    except Exception as e:
        raise RuntimeError(f"Failed to create bot from template: {e!s}") from e


def _print_created(bot_path: str, with_cogs: bool) -> None:
    """Print the post-create summary for a generated bot file."""
    if with_cogs:
        create_example_cog(bot_path)
    print_success("Bot created successfully!")
    files = f"  - {bot_path} (main bot file)"
    if with_cogs:
        cogs_dir = os.path.join(os.path.dirname(bot_path), "cogs")
        files += f"\n  - {cogs_dir}\n    - __init__.py\n    - basic.py (example cog)"
    print_info(f"""
Files created:
{files}

To start your bot:
  python {bot_path}

To add admin rights, pass admins={{"<your lxmf hash>"}} to LXMFBot in {bot_path}.
    """)


def is_safe_path(path: str, base_path: str | None = None) -> bool:
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


def run_debug_command(argv: list[str] | None = None) -> int:
    """Run the debugger CLI.

    Args:
        argv: Arguments after ``debug`` (sys.argv[2:] when called from main).

    Returns:
        Process exit code.

    """
    from .debugger import Debugger, default_report_path

    parser = argparse.ArgumentParser(
        prog="lxmfy debug",
        description="Diagnose send/receive connectivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lxmfy debug                         # Full doctor + auto-save report file
  lxmfy debug doctor --config ./config --output ./debug-report.txt
  lxmfy debug probe <hash> --request-path --wait 30
  lxmfy debug send <hash>
  lxmfy debug receive
  lxmfy debug compare <hash_a> <hash_b>
  lxmfy debug tips
  lxmfy debug --announce-test         # Also try a live announce
  NO_COLOR=1 lxmfy debug              # Disable ANSI colors

Reports are privacy-redacted by default (home paths and hashes truncated).
Pass the saved lxmfy-debug-*.txt file when asking for help.
        """,
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="doctor",
        choices=["doctor", "probe", "send", "receive", "compare", "tips"],
        help="Debug action (default: doctor)",
    )
    parser.add_argument(
        "destination",
        nargs="?",
        default=None,
        help="Destination hash for probe/send/compare",
    )
    parser.add_argument(
        "other",
        nargs="?",
        default=None,
        help="Second destination hash for compare",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Bot config directory (default: ./config)",
    )
    parser.add_argument(
        "--reticulum-config",
        default=None,
        help="Reticulum config directory override",
    )
    parser.add_argument(
        "--request-path",
        action="store_true",
        help="Request a path when probing a destination",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=0.0,
        help="Seconds to wait for a path after --request-path",
    )
    parser.add_argument(
        "--announce-test",
        action="store_true",
        help="Attempt a live announce_now (requires usable bot identity/router)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write report to this file path",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        default=True,
        help="Save a privacy-redacted report file (default on for doctor)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write a report file",
    )
    parser.add_argument(
        "--no-privacy",
        action="store_true",
        help="Do not redact home paths / hashes (local use only)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors (also respects NO_COLOR)",
    )

    args = parser.parse_args(argv)

    if args.no_color:
        Colors.set_enabled(False)

    dbg = Debugger(
        reticulum_config_dir=args.reticulum_config,
        config_path=args.config,
        privacy=not args.no_privacy,
    )

    should_save = (args.output is not None or args.save) and not args.no_save

    def _save(report):
        path = args.output or default_report_path(as_json=args.json)
        saved = dbg.save_report(report, path, as_json=args.json)
        if args.json:
            print(f"Report saved to {saved}", file=sys.stderr)
        else:
            print_success(f"Report saved to {saved}")
            print_info("Share that file when asking for help.")
        return saved

    if args.action == "tips":
        print_header("Send / Receive Tips")
        from .debugger import COMMON_TIPS

        for tip in COMMON_TIPS:
            print_info(tip)
        return 0

    if args.action == "compare":
        left = args.destination
        right = args.other
        if not left or not right:
            print_error("compare requires two destination hashes")
            print_info("Usage: lxmfy debug compare <hash_a> <hash_b>")
            return 1
        result = dbg.compare_destinations(
            left,
            right,
            request_path=args.request_path,
            wait=args.wait,
        )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print_header("Destination Compare")
            print_kv("both_valid", str(result["both_valid"]), ok=result["both_valid"])
            print_kv(
                "both_identity_known",
                str(result["both_identity_known"]),
                ok=result["both_identity_known"],
            )
            print_kv(
                "both_have_path",
                str(result["both_have_path"]),
                ok=result["both_have_path"],
            )
            print_section("Left")
            for k, v in result["left"].items():
                if k in {"notes", "hints", "timeline"}:
                    continue
                if v in (None, "", [], False) and k not in {
                    "valid_hash",
                    "identity_known",
                    "has_path",
                }:
                    continue
                print_kv(k, str(v))
            print_section("Right")
            for k, v in result["right"].items():
                if k in {"notes", "hints", "timeline"}:
                    continue
                if v in (None, "", [], False) and k not in {
                    "valid_hash",
                    "identity_known",
                    "has_path",
                }:
                    continue
                print_kv(k, str(v))
            for note in result.get("notes") or []:
                print_info(note)
        if should_save:
            report = dbg.run_doctor()
            report.compare = result
            _save(report)
        if not (
            result["both_valid"]
            and result["both_identity_known"]
            and result["both_have_path"]
        ):
            return 2
        return 0

    if args.action == "probe":
        dest = args.destination
        if not dest:
            print_error("probe requires a destination hash")
            print_info(
                "Usage: lxmfy debug probe <hash> [--request-path] [--wait N]",
            )
            return 1
        probe = dbg.probe_destination(
            dest,
            request_path=args.request_path,
            wait=args.wait,
        )
        dbg.print_probe(probe, as_json=args.json)
        if should_save:
            report = dbg.run_doctor(destination=dest)
            report.probe = probe
            _save(report)
        if not (probe.valid_hash and probe.identity_known and probe.has_path):
            return 2
        return 0

    if args.action == "send":
        dest = args.destination
        if not dest:
            print_error("send requires a destination hash")
            print_info("Usage: lxmfy debug send <hash>")
            return 1
        report = dbg.run_doctor(
            destination=dest,
            request_path=args.request_path,
            wait=args.wait,
            try_announce=args.announce_test,
        )
        if not args.json:
            print_header("Send Diagnosis")
            for check in dbg.diagnose_send(dest, probe=report.probe):
                print_check(check.name, check.status, check.detail, check.hint)
            if report.probe:
                dbg.print_probe(report.probe, as_json=False)
            print_section("Blockers")
            if report.send_blockers:
                for b in report.send_blockers:
                    print_error(b)
            else:
                print_success("No hard send blockers detected")
        else:
            dbg.print_report(report, as_json=True)
        if should_save:
            _save(report)
        fails = sum(1 for c in report.checks if c.status == "fail")
        return 2 if fails else 0

    if args.action == "receive":
        report = dbg.run_doctor(try_announce=args.announce_test)
        if args.json:
            dbg.print_report(report, as_json=True)
        else:
            print_header("Receive Diagnosis")
            recv_checks = [
                c
                for c in report.checks
                if c.category in {"receive", "announce", "network", "instance", "disk"}
            ]
            for check in recv_checks:
                print_check(check.name, check.status, check.detail, check.hint)
            print_section("Blockers")
            if report.receive_blockers:
                for b in report.receive_blockers:
                    print_error(b)
            else:
                print_success("No hard receive blockers detected")
        if should_save:
            _save(report)
        fails = sum(1 for c in report.checks if c.status == "fail")
        return 2 if fails else 0

    # doctor (default)
    dest = args.destination
    request_path = args.request_path or bool(dest)
    wait = args.wait
    if dest and request_path and wait <= 0:
        wait = 15.0
    report = dbg.run_doctor(
        destination=dest,
        request_path=request_path,
        wait=wait,
        try_announce=args.announce_test,
    )
    dbg.print_report(report, as_json=args.json)
    if should_save:
        _save(report)
    return 2 if report.to_dict()["failures"] else 0


def _ask(prompt: str, default: str, *, assume_yes: bool) -> str:
    """Prompt for a value, or return the default non-interactively."""
    if assume_yes or not sys.stdin.isatty():
        return default
    answer = input(f"{Colors.CYAN}{prompt} [{default}]: {Colors.ENDC}").strip()
    return answer or default


def _validate_admin_hashes(raw: str) -> list[str]:
    """Split and validate a comma-separated admin hash list."""
    hashes = []
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError(f"Admin hash is not hex: {value}") from exc
        hashes.append(value)
    return hashes


def run_init(argv: list[str] | None = None) -> int:
    """Interactive project scaffold.

    Creates a project directory with a configured bot.py, a cogs
    package, a README, and a .gitignore. Prompts for each option on a
    TTY; --yes or a non-TTY stdin accepts defaults and flags.
    """
    parser = argparse.ArgumentParser(
        prog="lxmfy init",
        description="Scaffold a new bot project interactively",
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Project directory and default bot name",
    )
    parser.add_argument(
        "--dir",
        dest="directory",
        default=None,
        help="Parent directory for the project (default: current)",
    )
    parser.add_argument(
        "--here",
        action="store_true",
        help="Scaffold into the current directory",
    )
    parser.add_argument(
        "--bot-name",
        default=None,
        help="Bot display name (default: project directory name)",
    )
    parser.add_argument(
        "--template",
        choices=["basic", "echo", "reminder", "note", "cogtest", "rrc"],
        default=None,
        help="Bot template (default: basic)",
    )
    parser.add_argument(
        "--storage",
        choices=["json", "sqlite", "msgpack", "memory"],
        default=None,
        help="Storage backend for a basic bot (default: json)",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Command prefix for a basic bot (default: /)",
    )
    parser.add_argument(
        "--admins",
        default=None,
        help="Comma-separated admin LXMF hashes",
    )
    parser.add_argument(
        "--no-cogs",
        action="store_true",
        help="Do not create the cogs package",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Accept defaults for every prompt",
    )
    args = parser.parse_args(argv)

    yes = args.yes

    if args.here:
        project_dir = os.path.abspath(args.directory or os.getcwd())
    else:
        dir_name = args.name or _ask(
            "Project directory",
            "mybot",
            assume_yes=yes,
        )
        project_dir = os.path.abspath(os.path.join(args.directory or ".", dir_name))

    default_bot_name = os.path.basename(project_dir.rstrip(os.sep)) or "mybot"
    bot_name = args.bot_name or _ask(
        "Bot name",
        default_bot_name,
        assume_yes=yes,
    )
    try:
        bot_name = validate_bot_name(bot_name)
    except ValueError as ve:
        print_error(f"Invalid bot name '{bot_name}': {ve}")
        return 1

    template = args.template or _ask(
        "Template (basic, echo, reminder, note, cogtest, rrc)",
        "basic",
        assume_yes=yes,
    )
    if template not in {"basic", "echo", "reminder", "note", "cogtest", "rrc"}:
        print_error(f"Invalid template '{template}'")
        return 1

    storage = "json"
    prefix = "/"
    admins: list[str] = []
    cogs = not args.no_cogs
    if template == "basic":
        storage = args.storage or _ask(
            "Storage (json, sqlite, msgpack, memory)",
            "json",
            assume_yes=yes,
        )
        if storage not in {"json", "sqlite", "msgpack", "memory"}:
            print_error(f"Invalid storage backend '{storage}'")
            return 1
        prefix = args.prefix or _ask(
            "Command prefix",
            "/",
            assume_yes=yes,
        )
        if not yes and sys.stdin.isatty() and not args.admins:
            raw = input(
                f"{Colors.CYAN}Admin LXMF hashes, comma-separated (optional): {Colors.ENDC}",
            ).strip()
        else:
            raw = args.admins or ""
        try:
            admins = _validate_admin_hashes(raw or (args.admins or ""))
        except ValueError as ve:
            print_error(str(ve))
            return 1
        if not args.no_cogs and not yes and sys.stdin.isatty():
            answer = (
                input(
                    f"{Colors.CYAN}Create example cogs package? [Y/n]: {Colors.ENDC}",
                )
                .strip()
                .lower()
            )
            cogs = answer not in {"n", "no"}

    if os.path.isdir(project_dir) and os.listdir(project_dir) and not args.force:
        if yes or not sys.stdin.isatty():
            print_error(
                f"Directory {project_dir} is not empty. Use --force to overwrite.",
            )
            return 1
        answer = (
            input(
                f"{Colors.CYAN}{project_dir} is not empty. Overwrite? [y/N]: {Colors.ENDC}",
            )
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            print_info("Aborted.")
            return 1

    os.makedirs(project_dir, exist_ok=True)
    bot_path = os.path.join(project_dir, "bot.py")

    template_map = {
        "echo": EchoBot,
        "reminder": ReminderBot,
        "note": NoteBot,
        "cogtest": CogTestBot,
        "rrc": RRCBot,
    }

    if template == "basic":
        admins_block = (
            "    admins={\n" + ",\n".join(f'        "{h}"' for h in admins) + "\n    },"
            if admins
            else "    # add your LXMF hash to admins\n    admins=set(),"
        )
        bot_source = f'''from lxmfy import LXMFBot

bot = LXMFBot(
    "{bot_name}",
    command_prefix="{prefix}",
    storage_type="{storage}",
    storage_path="data",
{admins_block}
    cogs_enabled={cogs},
)


@bot.command("hello", description="Say hello")
def hello(ctx):
    ctx.reply(f"Hello {{ctx.sender}}!")


if __name__ == "__main__":
    bot.run()
'''
    else:
        cls_name = template_map[template].__name__
        bot_source = f'''from lxmfy.templates import {cls_name}

if __name__ == "__main__":
    bot = {cls_name}(name="{bot_name}")
    bot.run()
'''

    with open(bot_path, "w", encoding="utf-8") as f:
        f.write(bot_source)

    if cogs:
        create_example_cog(bot_path)

    with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            f"# {bot_name}\n\n"
            "LXMFy bot project.\n\n"
            "## Run\n\n"
            "```bash\n"
            "pip install lxmfy\n"
            "python bot.py\n"
            "```\n\n"
            "The bot prints its LXMF address on startup. Add that address "
            "in your client and send `/help`.\n",
        )

    with open(os.path.join(project_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("config/\ndata/\n__pycache__/\n*.pyc\n")

    print_success(f"Project created in {project_dir}")
    print_info(
        f"Next: cd {os.path.relpath(project_dir)} && python bot.py",
    )
    return 0


def main() -> None:
    """Main CLI entry point."""
    try:
        init_colors()

        if len(sys.argv) == 1:
            interactive_mode()
            return

        # Fast-path debug and init before the create/run/signatures parser
        if len(sys.argv) >= 2 and sys.argv[1] == "debug":
            if "--no-color" in sys.argv or os.environ.get("NO_COLOR"):
                Colors.set_enabled(False)
            sys.exit(run_debug_command(sys.argv[2:]))

        if len(sys.argv) >= 2 and sys.argv[1] == "init":
            sys.exit(run_init(sys.argv[2:]))

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

  lxmfy debug                           # Diagnose send/receive connectivity
  lxmfy debug probe <hash> --request-path --wait 30
  lxmfy debug send <hash>
  lxmfy debug receive

  lxmfy signatures test                 # Test signature functionality
  lxmfy signatures enable               # Show how to enable signatures
  lxmfy signatures disable              # Show how to disable signatures
            """,
        )

        parser.add_argument(
            "command",
            choices=["create", "run", "signatures", "debug"],
            help="Create a bot file, run a template bot, debug messaging, or manage signatures",
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
            choices=["basic", "echo", "reminder", "note", "cogtest", "rrc"],
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
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="Disable ANSI colors (also respects NO_COLOR)",
        )

        args = parser.parse_args()

        if args.no_color:
            Colors.set_enabled(False)

        if args.command == "debug":
            # Reached if someone used a form that did not hit the fast-path
            remaining = []
            if args.name:
                remaining.append(args.name)
            if args.directory:
                remaining.append(args.directory)
            sys.exit(run_debug_command(remaining))

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
                _print_created(bot_path, with_cogs=args.template == "basic")
            except Exception as e:
                print_error(f"Error creating bot: {e!s}")
                sys.exit(1)

        elif args.command == "run":
            template_name = args.name
            if not template_name:
                print_error(
                    "Please specify a template name to run (echo, reminder, note, cogtest, rrc)",
                )
                sys.exit(1)

            template_map = {
                "echo": EchoBot,
                "reminder": ReminderBot,
                "note": NoteBot,
                "cogtest": CogTestBot,
                "rrc": RRCBot,
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

                if template_name == "rrc" and hasattr(bot_instance, "bot"):
                    hubs = bot_instance.bot.config.rrc_hubs or []
                    rooms = bot_instance.bot.config.rrc_rooms or []
                    rns_dir = getattr(bot_instance.bot, "reticulum_config_dir", None)
                    print_info(
                        f"RRC hubs: {', '.join(hubs) if hubs else '(none)'}",
                    )
                    print_info(
                        f"RRC rooms: {', '.join('#' + r for r in rooms) if rooms else '(none)'}",
                    )
                    print_info(f"Reticulum config: {rns_dir or '(default)'}")

                custom_name = args.name_opt
                if custom_name:
                    try:
                        validated_name = validate_bot_name(custom_name)
                        target: Any = getattr(bot_instance, "bot", bot_instance)
                        target.config.name = validated_name
                        target.name = validated_name
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
                                self.config = MockConfig()

                        class MockConfig:
                            identity_pinning_enabled = False

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
                            sender_identity=identity1,
                        )
                        if is_valid:
                            print_success("OK Signature verification successful")
                        else:
                            print_error("FAIL Signature verification failed")
                            sys.exit(1)

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
