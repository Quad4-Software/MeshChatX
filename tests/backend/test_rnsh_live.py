# SPDX-License-Identifier: 0BSD

"""Live RNSh session smoke tests.

These start a real rnsh listener through RNSHSession and wait for the listen
address to appear in process output. They are opt-in because they spawn a
Reticulum process and take a few seconds.

Enable with: MESHCHAT_LIVE_RNSH=1
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import textwrap
import time

import pytest

from meshchatx.src.backend.rnsh_manager import (
    RNSHSession,
    _MESHCHATX_RUN_MODULE_FLAG,
    _RNSH_MODULE,
)

_RUN = os.environ.get("MESHCHAT_LIVE_RNSH") == "1"
_RNSH_AVAILABLE = importlib.util.find_spec(_RNSH_MODULE) is not None


class _LiveManager:
    def __init__(self, reticulum_config_dir: str):
        self.reticulum_config_dir = reticulum_config_dir
        self.changes = 0

    def _on_session_change(self, _session):
        self.changes += 1

    def save(self):
        return None


def _force_pipe_mode(monkeypatch, session_cls=RNSHSession):
    # PTY children often get SIGHUP under pytest capture; use pipes for live smoke.
    monkeypatch.setattr(session_cls, "_supports_pty", staticmethod(lambda: False))


def _wait_for_listen_address(session: RNSHSession, timeout: float = 30.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if session.listen_address:
            return session.listen_address
        if session.status == RNSHSession.STATUS_FAILED:
            raise AssertionError(
                f"rnsh failed before listen address: {session.last_error!r} "
                f"output={session.to_dict(include_output_tail=True).get('output_text')!r}",
            )
        time.sleep(0.2)
    payload = session.to_dict(include_output_tail=True)
    raise AssertionError(
        f"timed out waiting for rnsh listen address; status={session.status} "
        f"output={payload.get('output_text')!r}",
    )


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RNSH=1 to run live RNSh tests")
@pytest.mark.skipif(
    not _RNSH_AVAILABLE, reason="RNS.Utilities.rnsh.rnsh is not installed"
)
def test_rnsh_live_listen_session_reports_address(monkeypatch):
    _force_pipe_mode(monkeypatch)
    tmpdir = tempfile.mkdtemp(prefix="meshchat_rnsh_live_")
    manager = _LiveManager(tmpdir)
    session = RNSHSession(
        manager,
        "live-listen",
        {
            "mode": "listen",
            "no_auth": True,
            "quiet": 1,
            "config_path": tmpdir,
        },
    )
    try:
        started = session.start()
        assert started["status"] == RNSHSession.STATUS_RUNNING
        assert started["pid"]
        assert "-m" in started["last_command"] or "rnsh" in started["last_command"]
        assert "--meshchatx-run-module" not in started["last_command"]
        assert session._build_env().get("PYTHONUNBUFFERED") == "1"

        address = _wait_for_listen_address(session)
        assert len(address) >= 16
        assert all(ch in "0123456789abcdef" for ch in address)
        assert session.status == RNSHSession.STATUS_RUNNING
    finally:
        session.stop()
        shutil.rmtree(tmpdir, ignore_errors=True)

    assert session.status == RNSHSession.STATUS_STOPPED
    assert session.listen_address


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RNSH=1 to run live RNSh tests")
@pytest.mark.skipif(
    not _RNSH_AVAILABLE, reason="RNS.Utilities.rnsh.rnsh is not installed"
)
def test_rnsh_live_meshchatx_run_module_launcher_starts_listener(monkeypatch, tmp_path):
    """Frozen-style launcher: MeshChatX re-entry flag, executed via a shim script."""
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    shim = tmp_path / "meshchatx_shim.py"
    shim.write_text(
        textwrap.dedent(
            """            import runpy
            import sys

            marker = "--meshchatx-run-module"
            if len(sys.argv) < 3 or sys.argv[1] != marker:
                raise SystemExit("shim expected --meshchatx-run-module")
            module_name = sys.argv[2]
            sys.argv = [sys.argv[0], *sys.argv[3:]]
            runpy.run_module(module_name, run_name="__main__", alter_sys=True)
            """
        ),
        encoding="utf-8",
    )

    real_python = rnsh_mod.sys.executable

    def _frozen_style_launcher():
        return [real_python, str(shim), _MESHCHATX_RUN_MODULE_FLAG, _RNSH_MODULE]

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_is_frozen_executable", lambda: True)
    monkeypatch.setattr(
        rnsh_mod.RNSHSession,
        "_resolve_rnsh_launcher",
        staticmethod(_frozen_style_launcher),
    )
    _force_pipe_mode(monkeypatch, rnsh_mod.RNSHSession)

    tmpdir = tempfile.mkdtemp(prefix="meshchat_rnsh_runmod_live_")
    manager = _LiveManager(tmpdir)
    session = rnsh_mod.RNSHSession(
        manager,
        "live-run-module",
        {
            "mode": "listen",
            "no_auth": True,
            "quiet": 1,
            "config_path": tmpdir,
        },
    )
    try:
        command = session._build_command()
        assert command[1:4] == [str(shim), _MESHCHATX_RUN_MODULE_FLAG, _RNSH_MODULE]
        assert "-m" not in command
        started = session.start()
        assert started["status"] == RNSHSession.STATUS_RUNNING
        assert _MESHCHATX_RUN_MODULE_FLAG in started["last_command"]
        address = _wait_for_listen_address(session)
        assert len(address) >= 16
    finally:
        session.stop()
        shutil.rmtree(tmpdir, ignore_errors=True)
