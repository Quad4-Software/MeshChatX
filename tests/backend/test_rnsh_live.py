# SPDX-License-Identifier: 0BSD

"""Live RNSh session smoke tests.

These start a real rnsh listener through RNSHSession and wait for the listen
address to appear in process output. They are opt-in because they spawn a
Reticulum process and take a few seconds.

Enable with: MESHCHAT_LIVE_RNSH=1
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import shutil
import socket
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
        self.outputs = 0

    def _on_session_change(self, _session):
        self.changes += 1

    def _on_session_output(self, _session, _chunk):
        self.outputs += 1

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


def _write_tcp_pair(listen_dir: str, conn_dir: str, port: int) -> None:
    listen_cfg = textwrap.dedent(
        f"""\
        [reticulum]
          enable_transport = Yes
          share_instance = No
          shared_instance_port = {37000 + (port % 1000)}
          instance_name = rnsh_live_listen_{port}
          panic_on_interface_error = No

        [logging]
          loglevel = 4

        [interfaces]
          [[TCP Server]]
            type = TCPServerInterface
            enabled = Yes
            listen_ip = 127.0.0.1
            listen_port = {port}
        """
    )
    conn_cfg = textwrap.dedent(
        f"""\
        [reticulum]
          enable_transport = Yes
          share_instance = No
          shared_instance_port = {38000 + (port % 1000)}
          instance_name = rnsh_live_conn_{port}
          panic_on_interface_error = No

        [logging]
          loglevel = 4

        [interfaces]
          [[TCP Client]]
            type = TCPClientInterface
            enabled = Yes
            target_host = 127.0.0.1
            target_port = {port}
        """
    )
    os.makedirs(listen_dir, exist_ok=True)
    os.makedirs(conn_dir, exist_ok=True)
    with open(os.path.join(listen_dir, "config"), "w", encoding="utf-8") as handle:
        handle.write(listen_cfg)
    with open(os.path.join(conn_dir, "config"), "w", encoding="utf-8") as handle:
        handle.write(conn_cfg)


def _wait_for_output(
    session: RNSHSession,
    needle: str,
    timeout: float = 35.0,
) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = session.to_dict(include_output_tail=True)
        text = payload.get("output_text") or ""
        if needle in text:
            return text
        if session.status == RNSHSession.STATUS_FAILED:
            raise AssertionError(
                f"session failed before output {needle!r}: {session.last_error!r} "
                f"output={text!r}",
            )
        if (
            session.status != RNSHSession.STATUS_RUNNING
            and needle not in text
            and session._process is None
        ):
            payload = session.to_dict(include_output_tail=True)
            text = payload.get("output_text") or ""
            if needle in text:
                return text
            raise AssertionError(
                f"session stopped before output {needle!r}; status={session.status} "
                f"exit={session.last_exit_code} output={text!r}",
            )
        time.sleep(0.25)
    payload = session.to_dict(include_output_tail=True)
    raise AssertionError(
        f"timed out waiting for {needle!r}; status={session.status} "
        f"output={payload.get('output_text')!r}",
    )


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RNSH=1 to run live RNSh tests")
@pytest.mark.skipif(
    not _RNSH_AVAILABLE, reason="RNS.Utilities.rnsh.rnsh is not installed"
)
@pytest.mark.skipif(os.name != "posix", reason="Full connect e2e requires a PTY")
def test_rnsh_live_listen_connect_echo_roundtrip():
    """Full initiator/listener path over a local TCP Reticulum link.

    Connect mode must use a real PTY: rnsh's initiator registers stdin with
    asyncio, which fails under pipe/DEVNULL (PermissionError) and never runs
    the remote command.
    """
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    listen_dir = tempfile.mkdtemp(prefix="meshchat_rnsh_e2e_listen_")
    conn_dir = tempfile.mkdtemp(prefix="meshchat_rnsh_e2e_conn_")
    _write_tcp_pair(listen_dir, conn_dir, port)

    listen_manager = _LiveManager(listen_dir)
    conn_manager = _LiveManager(conn_dir)
    listen = RNSHSession(
        listen_manager,
        "e2e-listen",
        {
            "mode": "listen",
            "no_auth": True,
            "quiet": 1,
            "config_path": listen_dir,
            "announce_period": 2,
        },
    )
    connect = RNSHSession(
        conn_manager,
        "e2e-connect",
        {
            "mode": "connect",
            "destination": "pending",
            "config_path": conn_dir,
            "remote_command": "echo MESHCHAT_RNSH_E2E_OK",
            "quiet": 1,
            "timeout": 25,
            "mirror": True,
        },
    )
    try:
        listen.start()
        address = _wait_for_listen_address(listen, timeout=30.0)
        listen_text = (
            listen.to_dict(include_output_tail=True).get("output_text") or ""
        ).lower()
        assert f"listening for commands on <{address}>" in listen_text

        # Allow TCP link + announce to settle before the initiator path request.
        time.sleep(2.0)

        connect.config["destination"] = address
        connect.start()
        assert connect.status == RNSHSession.STATUS_RUNNING
        assert connect._master_fd is not None

        output = _wait_for_output(connect, "MESHCHAT_RNSH_E2E_OK", timeout=35.0)
        assert "MESHCHAT_RNSH_E2E_OK" in output

        deadline = time.time() + 15.0
        while time.time() < deadline and connect.status == RNSHSession.STATUS_RUNNING:
            time.sleep(0.2)
        assert connect.status in (
            RNSHSession.STATUS_STOPPED,
            RNSHSession.STATUS_FAILED,
        )
        if connect.last_exit_code is not None:
            assert connect.last_exit_code == 0
    finally:
        with contextlib.suppress(Exception):
            connect.stop()
        with contextlib.suppress(Exception):
            listen.stop()
        shutil.rmtree(listen_dir, ignore_errors=True)
        shutil.rmtree(conn_dir, ignore_errors=True)
