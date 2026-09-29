import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lxmfy import BotConfig, LXMFBot
from lxmfy.cogs_core import load_cogs_from_directory


def is_bwrap_functional():
    """Check if bwrap can actually run a simple command in this environment."""
    try:
        # Construct a realistic minimal bwrap command
        cmd = ["bwrap", "--unshare-all", "--ro-bind", "/usr", "/usr"]
        for p in ["/bin", "/lib", "/lib64", "/sbin"]:
            if os.path.islink(p):
                cmd.extend(["--symlink", os.readlink(p), p])
            elif os.path.exists(p):
                cmd.extend(["--ro-bind", p, p])
        cmd.extend(["/usr/bin/true"])

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture
def realistic_cogs_setup():
    """Set up a temporary directory with various language cogs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        cogs_dir = temp_path / "cogs"
        cogs_dir.mkdir()

        # 1. Bash Cog
        bash_path = cogs_dir / "bash_hello"
        bash_path.write_text('#!/bin/bash\necho "Bash: Hello $1"')
        os.chmod(bash_path, os.stat(bash_path).st_mode | stat.S_IEXEC)

        # 2. Perl Cog
        perl_path = cogs_dir / "perl_hello"
        perl_path.write_text('#!/usr/bin/perl\nprint "Perl: Hello $ARGV[0]\\n";')
        os.chmod(perl_path, os.stat(perl_path).st_mode | stat.S_IEXEC)

        # 3. C Cog
        c_bin = None
        if shutil.which("gcc"):
            c_src = temp_path / "hello.c"
            c_src.write_text("""
    #include <stdio.h>
    int main(int argc, char *argv[]) {
        if (argc > 1) {
            printf("C: Hello %s\\n", argv[1]);
        }
        return 0;
    }
    """)
            c_bin = cogs_dir / "c_hello"
            subprocess.run(["gcc", str(c_src), "-o", str(c_bin)], check=True)
            # os.chmod is usually set by gcc, but let's be sure
            os.chmod(c_bin, os.stat(c_bin).st_mode | stat.S_IEXEC)

        # 4. Go Cog
        go_bin = None
        if shutil.which("go"):
            go_src = temp_path / "hello.go"
            go_src.write_text("""
    package main
    import (
        "fmt"
        "os"
    )
    func main() {
        if len(os.Args) > 1 {
            fmt.Printf("Go: Hello %s\\n", os.Args[1])
        }
    }
    """)
            go_bin = cogs_dir / "go_hello"
            # Compile with CGO_ENABLED=0 for a static binary (easier for sandbox)
            env = os.environ.copy()
            env["CGO_ENABLED"] = "0"
            subprocess.run(
                ["go", "build", "-o", str(go_bin), str(go_src)],
                env=env,
                check=True,
            )

        yield temp_path


def test_multilang_cogs_execution(realistic_cogs_setup):
    """Test that cogs in different languages execute correctly without sandbox."""
    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=True,
        external_cogs_sandbox_enabled=False,
        config_path=str(realistic_cogs_setup),
        storage_path=str(realistic_cogs_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(realistic_cogs_setup)

    load_cogs_from_directory(bot)

    languages = {
        "bash_hello": "Bash: Hello test_sender",
        "perl_hello": "Perl: Hello test_sender",
    }
    if shutil.which("gcc"):
        languages["c_hello"] = "C: Hello test_sender"
    if shutil.which("go"):
        languages["go_hello"] = "Go: Hello test_sender"

    for cmd_name, expected_output in languages.items():
        assert cmd_name in bot.commands
        msg = MagicMock()
        msg.sender = "test_sender"
        msg.content = f"/{cmd_name}"
        msg.args = []

        bot.commands[cmd_name].callback(msg)
        msg.reply.assert_called_with(expected_output)


@pytest.mark.skipif(
    not is_bwrap_functional(),
    reason="bwrap is not functional in this environment",
)
def test_bwrap_sandbox_isolation(realistic_cogs_setup):
    """Test that bwrap sandbox actually isolates the process."""
    # Create a script that tries to read a file outside the sandbox
    secret_file = realistic_cogs_setup / "host_secret.txt"
    secret_file.write_text("HOST_SECRET_DATA")

    cogs_dir = realistic_cogs_setup / "cogs"
    leak_script = cogs_dir / "leak_test"
    # Try to cat a file that isn't bound in bwrap
    leak_script.write_text(f"#!/bin/bash\ncat {secret_file} 2>&1")
    os.chmod(leak_script, os.stat(leak_script).st_mode | stat.S_IEXEC)

    config = BotConfig(
        name="TestBot",
        test_mode=True,
        external_cogs_enabled=True,
        external_cogs_sandbox_enabled=True,
        external_cogs_sandbox_type="bwrap",
        config_path=str(realistic_cogs_setup),
        storage_path=str(realistic_cogs_setup / "storage"),
    )
    bot = LXMFBot(**config.__dict__)
    bot.config_path = str(realistic_cogs_setup)

    load_cogs_from_directory(bot)

    msg = MagicMock()
    msg.sender = "test_sender"
    bot.commands["leak_test"].callback(msg)

    # It should fail to read the file
    args, _ = msg.reply.call_args
    output = args[0]
    # The handler replies with "Error executing command: ..." on non-zero exit
    assert "Error executing command" in output
    assert "HOST_SECRET_DATA" not in output
