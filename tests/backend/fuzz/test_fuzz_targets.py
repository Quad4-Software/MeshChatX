# SPDX-License-Identifier: 0BSD
"""Bounded coverage-guided fuzzing of RRC parsers.

Each libFuzzer target runs as a subprocess so an abort cannot take down
the pytest process. A finding exits non-zero with a minimized crash
artifact. Fuzzing stays on local in-process bytes - no network.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FUZZ_DIR = Path(__file__).resolve().parent
RUNS = int(os.environ.get("MESHCHAT_FUZZ_RUNS", "100000"))
TIMEOUT = int(os.environ.get("MESHCHAT_FUZZ_TIMEOUT", "90"))

TARGETS = ["decode", "room_list", "room_name", "who"]


@pytest.mark.parametrize("target", TARGETS)
def test_fuzz_target(target, tmp_path):
    env = dict(os.environ)
    proc = subprocess.run(
        [
            sys.executable,
            str(FUZZ_DIR / "fuzz_rrc_protocol.py"),
            target,
            f"-runs={RUNS}",
            "-max_len=4096",
            f"-artifact_prefix={tmp_path}/",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        cwd=str(FUZZ_DIR.parent.parent),
    )
    crashes = list(tmp_path.glob("crash-*"))
    assert proc.returncode == 0 and not crashes, (
        f"fuzz target {target} found a crash:\n"
        f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )
