# SPDX-License-Identifier: 0BSD

"""Sanity checks for the Android emulator smoke CI script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "ci" / "android-emulator-smoke.sh"


def test_smoke_script_exists_and_is_executable():
    assert _SCRIPT.is_file()
    assert os.access(_SCRIPT, os.X_OK)


def test_smoke_script_bash_syntax():
    subprocess.run(["bash", "-n", str(_SCRIPT)], check=True)


def test_smoke_script_requires_apk_arg():
    proc = subprocess.run(
        ["bash", str(_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "usage:" in (proc.stderr + proc.stdout)


def test_workflow_references_smoke_script():
    workflow = (
        _REPO / ".github" / "workflows" / "android-emulator-smoke.yml"
    ).read_text(encoding="utf-8")
    assert "scripts/ci/android-emulator-smoke.sh" in workflow
    assert "reactivecircus/android-emulator-runner@" in workflow
    assert "MESHCHATX_ABIS" in workflow
    assert "x86_64" in workflow
    # Runner executes each script: line with /usr/bin/sh (dash). A bare
    # set -euo pipefail there fails with "Illegal option -o pipefail".
    smoke_step = workflow.split("name: Run emulator smoke", 1)[1]
    smoke_script = smoke_step.split("script:", 1)[1].split("\n", 1)[0]
    assert "bash scripts/ci/android-emulator-smoke.sh" in smoke_script
    assert "set -euo pipefail" not in smoke_script
