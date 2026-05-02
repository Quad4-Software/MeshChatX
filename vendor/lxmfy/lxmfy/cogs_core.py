"""Cogs management module for LXMFy.

This module provides functionality for loading and managing cogs (extension modules)
in LXMFy bots. It handles dynamic loading of Python modules from a specified directory
and manages their integration with the bot system.
"""

import os
import shutil
import subprocess
import sys

import RNS


def _get_sandbox_command(bot, script_path):
    """Determines the sandbox command to use for external cogs."""
    if not bot.config.external_cogs_sandbox_enabled:
        return None

    if sys.platform != "linux":
        return None

    sandbox_type = bot.config.external_cogs_sandbox_type.lower()

    # Detect available tools
    bwrap_path = shutil.which("bwrap")
    firejail_path = shutil.which("firejail")

    if sandbox_type == "bwrap" or (sandbox_type == "auto" and bwrap_path):
        if bwrap_path:
            # Minimal bwrap sandbox
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

            # Handle merged-usr systems by creating symlinks if they are symlinks on host
            for path in ["/bin", "/lib", "/lib64", "/sbin"]:
                if os.path.islink(path):
                    target = os.readlink(path)
                    # If target is relative, we keep it relative, but bwrap --symlink takes (target, dest)
                    cmd.extend(["--symlink", target, path])
                elif os.path.exists(path):
                    cmd.extend(["--ro-bind", path, path])

            # Add /etc/alternatives for things like python/ruby symlinks
            if os.path.exists("/etc/alternatives"):
                cmd.extend(["--ro-bind", "/etc/alternatives", "/etc/alternatives"])

            # Bind the script itself
            cmd.extend(["--ro-bind", script_path, script_path])

            return cmd

    if sandbox_type == "firejail" or (sandbox_type == "auto" and firejail_path):
        if firejail_path:
            return [firejail_path, "--quiet", "--private", "--net=none", "--noprofile"]

    return None


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

                            # Apply sandbox if enabled and available
                            sandbox_cmd = _get_sandbox_command(bot, script_path)
                            if sandbox_cmd:
                                full_cmd = sandbox_cmd + [script_path] + script_args
                            else:
                                full_cmd = [script_path] + script_args

                            # Determine timeout (0 or None means no timeout)
                            timeout = bot.config.external_cogs_timeout
                            if timeout <= 0:
                                timeout = None

                            result = subprocess.run(  # noqa: S603
                                full_cmd,
                                capture_output=True,
                                text=True,
                                env=env,
                                check=True,
                                timeout=timeout,
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
