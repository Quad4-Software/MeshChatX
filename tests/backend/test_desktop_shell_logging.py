# SPDX-License-Identifier: 0BSD
"""Reference: desktop-shell backends leave meshchatx.log to the Go spool."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _import_handler_names(tmp_path: Path, desktop_shell: bool) -> list[str]:
    env = os.environ.copy()
    env["MESHCHAT_LOG_DIR"] = str(tmp_path / "logs")
    if desktop_shell:
        env["MESHCHATX_DESKTOP_SHELL"] = "1"
    else:
        env.pop("MESHCHATX_DESKTOP_SHELL", None)
    code = (
        "import json; import meshchatx.meshchat as m; "
        "print(json.dumps([type(h).__name__ for h in m.handlers]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_desktop_shell_skips_python_meshchat_log_file_handler(tmp_path):
    handlers = _import_handler_names(tmp_path, desktop_shell=True)
    assert "SafeRotatingFileHandler" not in handlers
    assert "StreamHandler" in handlers
    assert "PersistentLogHandler" in handlers


def test_non_desktop_keeps_python_meshchat_log_file_handler(tmp_path):
    handlers = _import_handler_names(tmp_path, desktop_shell=False)
    assert "SafeRotatingFileHandler" in handlers
    assert "StreamHandler" in handlers
    assert "PersistentLogHandler" in handlers
