"""Cogs management module for LXMFy.

This module provides functionality for loading and managing cogs (extension modules)
in LXMFy bots. It handles dynamic loading of Python modules from a specified directory
and manages their integration with the bot system.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

import RNS


@dataclass
class SandboxSetup:
    """Sandbox configuration for an external cog subprocess."""

    cmd_prefix: list[str] | None = None
    preexec_fn: Callable[[], None] | None = None


def _landlock_available(bot) -> bool:
    from .landlock_sandbox import landlock_requested

    return landlock_requested(bot.config.landlock_enabled)


def _make_cog_landlock_preexec(bot, script_path: str) -> Callable[[], None]:
    from .landlock_sandbox import apply_landlock_sandbox

    script_dir = os.path.dirname(os.path.abspath(script_path))

    def _preexec() -> None:
        apply_landlock_sandbox(
            extra_read_paths=[script_dir, script_path],
            temp_only=True,
            config_enabled=bot.config.landlock_enabled,
        )

    return _preexec


def _get_sandbox_setup(bot, script_path: str) -> SandboxSetup | None:
    """Determine sandbox settings for an external cog subprocess."""
    if not bot.config.external_cogs_sandbox_enabled:
        return None

    if sys.platform != "linux":
        return None

    sandbox_type = bot.config.external_cogs_sandbox_type.lower()

    if sandbox_type == "none":
        return None

    if sandbox_type == "landlock" or (
        sandbox_type == "auto" and _landlock_available(bot)
    ):
        if _landlock_available(bot):
            return SandboxSetup(preexec_fn=_make_cog_landlock_preexec(bot, script_path))

    bwrap_path = shutil.which("bwrap")
    firejail_path = shutil.which("firejail")

    if sandbox_type == "bwrap" or (sandbox_type == "auto" and bwrap_path):
        if bwrap_path:
            cmd = [
                bwrap_path,
                "--unshare-all",
                "--new-session",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",  # noqa: S108
                "--ro-bind",
                "/usr",
                "/usr",
            ]

            for path in ["/bin", "/lib", "/lib64", "/sbin"]:
                if os.path.islink(path):
                    target = os.readlink(path)
                    cmd.extend(["--symlink", target, path])
                elif os.path.exists(path):
                    cmd.extend(["--ro-bind", path, path])

            if os.path.exists("/etc/alternatives"):
                cmd.extend(["--ro-bind", "/etc/alternatives", "/etc/alternatives"])

            cmd.extend(["--ro-bind", script_path, script_path])
            return SandboxSetup(cmd_prefix=cmd)

    if sandbox_type == "firejail" or (sandbox_type == "auto" and firejail_path):
        if firejail_path:
            return SandboxSetup(
                cmd_prefix=[
                    firejail_path,
                    "--quiet",
                    "--private",
                    "--net=none",
                    "--noprofile",
                ],
            )

    return None


def _get_sandbox_command(bot, script_path):
    """Determines the sandbox command prefix to use for external cogs."""
    setup = _get_sandbox_setup(bot, script_path)
    if setup is None:
        return None
    return setup.cmd_prefix


def load_cogs_from_directory(bot, directory="cogs"):
    """Loads all Python modules and executable scripts from a directory.

    Args:
        bot: The LXMFBot instance to load the cogs into.
        directory (str): The directory name relative to the bot's config path. Defaults to "cogs".

    Raises:
        Exception: If there's an error loading any cog.

    """
    cogs_dir = os.path.join(bot.config_path, directory)

    if not os.path.exists(cogs_dir):
        os.makedirs(cogs_dir)
        RNS.log(f"Created cogs directory: {cogs_dir}", RNS.LOG_INFO)
        return

    if cogs_dir not in sys.path:
        sys.path.insert(0, os.path.dirname(cogs_dir))

    for filename in os.listdir(cogs_dir):
        if filename.startswith("_"):
            continue

        path = os.path.join(cogs_dir, filename)

        if filename.endswith(".py"):
            cog_name = f"{directory}.{filename[:-3]}"
            try:
                bot.load_extension(cog_name)
                RNS.log(f"Loaded extension: {cog_name}", RNS.LOG_INFO)
            except Exception as e:  # pylint: disable=broad-except
                RNS.log(f"Failed to load extension {cog_name}: {e!s}", RNS.LOG_ERROR)
        elif bot.config.external_cogs_enabled and os.access(path, os.X_OK):
            # Load as an external script cog
            command_name = os.path.splitext(filename)[0]
            try:
                from .commands import Command

                def create_handler(script_path, script_filename):
                    def handler(msg):
                        try:
                            env = os.environ.copy()
                            env["LXMFY_SENDER"] = msg.sender
                            env["LXMFY_CONTENT"] = msg.content
                            env["LXMFY_HAS_ADMIN"] = str(
                                getattr(msg, "is_admin", False),
                            ).lower()

                            # Prepare arguments: sender, content, and any existing args
                            script_args = [msg.sender, msg.content]
                            if hasattr(msg, "args") and msg.args:
                                script_args.extend([str(a) for a in msg.args])

                            timeout = bot.config.external_cogs_timeout
                            if timeout <= 0:
                                timeout = None

                            # Apply sandbox if enabled and available
                            sandbox_setup = _get_sandbox_setup(bot, script_path)
                            if sandbox_setup and sandbox_setup.cmd_prefix:
                                full_cmd = (
                                    sandbox_setup.cmd_prefix
                                    + [script_path]
                                    + script_args
                                )
                            else:
                                full_cmd = [script_path] + script_args

                            run_kwargs: dict = {
                                "capture_output": True,
                                "text": True,
                                "env": env,
                                "check": True,
                                "timeout": timeout,
                            }
                            if sandbox_setup and sandbox_setup.preexec_fn:
                                run_kwargs["preexec_fn"] = sandbox_setup.preexec_fn

                            result = subprocess.run(  # noqa: S603
                                full_cmd,
                                **run_kwargs,
                            )
                            if result.stdout.strip():
                                msg.reply(result.stdout.strip())
                            if result.stderr.strip():
                                RNS.log(
                                    f"External cog {script_filename} stderr: {result.stderr.strip()}",
                                    RNS.LOG_DEBUG,
                                )
                        except subprocess.TimeoutExpired:
                            RNS.log(
                                f"External cog {script_filename} timed out after {bot.config.external_cogs_timeout}s",
                                RNS.LOG_ERROR,
                            )
                            msg.reply(f"Error: Command {script_filename} timed out.")
                        except subprocess.CalledProcessError as e:
                            RNS.log(
                                f"External cog {script_filename} failed with exit code {e.returncode}: {e.stderr}",
                                RNS.LOG_ERROR,
                            )
                            msg.reply(f"Error executing command: {script_filename}")
                        except Exception as e:
                            RNS.log(
                                f"Unexpected error executing external cog {script_filename}: {e!s}",
                                RNS.LOG_ERROR,
                            )

                    return handler

                cmd = Command(
                    name=command_name,
                    description=f"External script command: {filename}",
                    threaded=True,  # Always threaded for external processes
                )
                cmd.callback = create_handler(path, filename)
                bot.commands[command_name] = cmd
                RNS.log(f"Loaded external extension: {filename}", RNS.LOG_INFO)
            except Exception as e:
                RNS.log(
                    f"Failed to load external extension {filename}: {e!s}",
                    RNS.LOG_ERROR,
                )
