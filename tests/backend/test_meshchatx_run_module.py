# SPDX-License-Identifier: 0BSD

"""Tests for MeshChatX ``--meshchatx-run-module`` frozen re-entry."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from meshchatx.meshchat import _maybe_run_embedded_module
from tests.backend.support.test_temp_dir import subprocess_test_env


def test_maybe_run_embedded_module_noop_without_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["meshchatx", "--headless"])
    assert _maybe_run_embedded_module() is False


def test_maybe_run_embedded_module_requires_module_name(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["meshchatx", "--meshchatx-run-module"])
    assert _maybe_run_embedded_module() is False


def test_maybe_run_embedded_module_rejects_flag_as_module_name(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["meshchatx", "--meshchatx-run-module", "--headless"],
    )
    with pytest.raises(SystemExit) as exc:
        _maybe_run_embedded_module()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--meshchatx-run-module requires a module name" in err


def test_maybe_run_embedded_module_runs_probe_and_rewrites_argv(
    monkeypatch,
    tmp_path,
):
    marker = tmp_path / "probe.out"
    monkeypatch.setenv("MESHCHATX_RUN_MODULE_PROBE_PATH", str(marker))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "meshchatx",
            "--meshchatx-run-module",
            "tests.backend.support.run_module_probe",
            "--alpha",
            "1",
        ],
    )
    assert _maybe_run_embedded_module() is True
    assert marker.read_text(encoding="utf-8") == "ok\n--alpha 1\n"
    assert sys.argv[0] == "meshchatx"
    assert sys.argv[1:] == ["--alpha", "1"]


def test_meshchat_main_dispatches_run_module_before_app_startup(
    monkeypatch,
    tmp_path,
):
    from meshchatx import meshchat as meshchat_mod

    marker = tmp_path / "probe.out"
    monkeypatch.setenv("MESHCHATX_RUN_MODULE_PROBE_PATH", str(marker))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "meshchatx",
            "--meshchatx-run-module",
            "tests.backend.support.run_module_probe",
            "from-main",
        ],
    )

    called = {"crash": False}

    def _boom():
        called["crash"] = True
        raise AssertionError("CrashRecovery must not run for module re-entry")

    monkeypatch.setattr(meshchat_mod, "CrashRecovery", _boom)
    meshchat_mod.main()
    assert called["crash"] is False
    assert marker.read_text(encoding="utf-8") == "ok\nfrom-main\n"


def test_meshchatx_run_module_subprocess_live(tmp_path):
    marker = tmp_path / "probe.out"
    env = subprocess_test_env(
        {
            "MESHCHATX_RUN_MODULE_PROBE_PATH": str(marker),
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        },
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "meshchatx.meshchat",
            "--meshchatx-run-module",
            "tests.backend.support.run_module_probe",
            "live-arg",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "meshchatx-run-module-probe live-arg" in result.stdout
    assert marker.read_text(encoding="utf-8") == "ok\nlive-arg\n"


def test_meshchatx_run_module_subprocess_can_invoke_rnsh_help():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "meshchatx.meshchat",
            "--meshchatx-run-module",
            "RNS.Utilities.rnsh.rnsh",
            "--help",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=subprocess_test_env(),
    )
    combined = result.stdout + result.stderr
    # rnsh prints help to stdout and exits 1 (argparse with no destination).
    assert result.returncode in (0, 1), combined
    assert "usage:" in combined.lower() or "rnsh" in combined.lower()
    assert "-l" in combined
    assert "unrecognized arguments: -m" not in combined
    assert "unrecognized arguments: --meshchatx-run-module" not in combined
