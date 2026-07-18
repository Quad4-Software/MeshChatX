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
import sys
import tempfile
import textwrap
import time

import pytest

from meshchatx.src.backend.rnsh_manager import (
    _MESHCHATX_RUN_MODULE_FLAG,
    _RNSH_MODULE,
    RNSHSession,
)

_RUN = os.environ.get("MESHCHAT_LIVE_RNSH") == "1"
_RNSH_AVAILABLE = importlib.util.find_spec(_RNSH_MODULE) is not None


class _LiveManager:
    def __init__(self, reticulum_config_dir: str, storage_dir: str | None = None):
        self.reticulum_config_dir = reticulum_config_dir
        # rnsh subprocess HOME is rooted under storage_dir (Landlock RW tree).
        self.storage_dir = storage_dir or reticulum_config_dir
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
    not _RNSH_AVAILABLE,
    reason="RNS.Utilities.rnsh.rnsh is not installed",
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
        env = session._build_env()
        assert env["HOME"] == os.path.join(tmpdir, "rnsh_home")
        assert os.path.isdir(os.path.join(tmpdir, "rnsh_home", ".rnsh"))

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
    not _RNSH_AVAILABLE,
    reason="RNS.Utilities.rnsh.rnsh is not installed",
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
            """,
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
        """,
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
        """,
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
    not _RNSH_AVAILABLE,
    reason="RNS.Utilities.rnsh.rnsh is not installed",
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_isolated_rns_config(config_dir: str, *, port: int, name: str) -> None:
    os.makedirs(config_dir, exist_ok=True)
    path = os.path.join(config_dir, "config")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            textwrap.dedent(
                f"""\
                [reticulum]
                  enable_transport = No
                  share_instance = No
                  shared_instance_port = {port}
                  instance_name = {name}
                  panic_on_interface_error = No

                [logging]
                  loglevel = 6
                """,
            ),
        )


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RNSH=1 to run live RNSh tests")
@pytest.mark.skipif(
    not _RNSH_AVAILABLE,
    reason="RNS.Utilities.rnsh.rnsh is not installed",
)
@pytest.mark.skipif(sys.platform != "linux", reason="Landlock live check is Linux-only")
def test_rnsh_live_listen_without_landlock(monkeypatch):
    """Landlock off: listener starts and HOME stays under storage."""
    monkeypatch.setenv("MESHCHAT_LANDLOCK", "0")
    _force_pipe_mode(monkeypatch)
    storage = tempfile.mkdtemp(prefix="meshchat_rnsh_ll_off_storage_")
    rns_dir = tempfile.mkdtemp(prefix="meshchat_rnsh_ll_off_rns_")
    session = None
    try:
        _write_isolated_rns_config(rns_dir, port=_free_port(), name="rnsh_ll_off")
        manager = _LiveManager(rns_dir, storage_dir=storage)
        session = RNSHSession(
            manager,
            "live-ll-off",
            {
                "mode": "listen",
                "no_auth": True,
                "quiet": 1,
                "config_path": rns_dir,
            },
        )
        started = session.start()
        assert started["status"] == RNSHSession.STATUS_RUNNING
        env = session._build_env()
        assert env["HOME"] == os.path.join(storage, "rnsh_home")
        address = _wait_for_listen_address(session, timeout=35.0)
        assert len(address) >= 16
        assert "Could not get or create rnsh configuration directory" not in (
            session.to_dict(include_output_tail=True).get("output_text") or ""
        )
    finally:
        if session is not None:
            with contextlib.suppress(Exception):
                session.stop()
        shutil.rmtree(storage, ignore_errors=True)
        shutil.rmtree(rns_dir, ignore_errors=True)


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RNSH=1 to run live RNSh tests")
@pytest.mark.skipif(
    not _RNSH_AVAILABLE,
    reason="RNS.Utilities.rnsh.rnsh is not installed",
)
@pytest.mark.skipif(sys.platform != "linux", reason="Landlock live check is Linux-only")
def test_rnsh_live_listen_under_landlock_and_denied_home_fails():
    """Landlock on + real HOME outside RW roots: rnsh cannot create ~/.rnsh."""
    import subprocess
    import sys
    from pathlib import Path

    from meshchatx.src.backend.landlock_sandbox import landlock_kernel_supported

    if not landlock_kernel_supported():
        pytest.skip("Landlock not available on this kernel")

    storage = tempfile.mkdtemp(prefix="meshchat_rnsh_ll_deny_storage_")
    rns_dir = tempfile.mkdtemp(prefix="meshchat_rnsh_ll_deny_rns_")
    _write_isolated_rns_config(rns_dir, port=_free_port(), name="rnsh_ll_deny")
    script = textwrap.dedent(
        f"""\
        import os
        import subprocess
        import sys
        from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox

        storage = {storage!r}
        rns_dir = {rns_dir!r}
        os.environ["MESHCHAT_LANDLOCK"] = "1"
        # HOME outside the Landlock RW tree (storage/tmp/run/dev).
        os.environ["HOME"] = "/root"
        os.environ.pop("XDG_CONFIG_HOME", None)
        ok = apply_landlock_sandbox(
            storage_dir=storage,
            reticulum_config_dir=rns_dir,
            log_dir=storage,
        )
        if not ok:
            print("LANDLOCK_NOT_APPLIED")
            sys.exit(2)
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "RNS.Utilities.rnsh.rnsh",
                "-c",
                rns_dir,
                "-l",
                "-n",
                "-q",
            ],
            capture_output=True,
            text=True,
            timeout=12,
            env=env,
            check=False,
        )
        out = (result.stdout or "") + (result.stderr or "")
        print("RC", result.returncode)
        print("OUT", out[-2000:])
        if "Could not get or create rnsh configuration directory" in out:
            print("GOT_CONFIG_DIR_CRITICAL")
            sys.exit(0)
        # Some environments may fail earlier with PermissionError on /root.
        if result.returncode not in (0, None) and (
            "Permission" in out or "configuration directory" in out
        ):
            print("GOT_HOME_DENY")
            sys.exit(0)
        print("UNEXPECTED_SUCCESS")
        sys.exit(3)
        """,
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        if "LANDLOCK_NOT_APPLIED" in result.stdout:
            pytest.skip("Landlock could not be applied in this environment")
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert (
            "GOT_CONFIG_DIR_CRITICAL" in result.stdout
            or "GOT_HOME_DENY" in result.stdout
        )
    finally:
        shutil.rmtree(storage, ignore_errors=True)
        shutil.rmtree(rns_dir, ignore_errors=True)


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RNSH=1 to run live RNSh tests")
@pytest.mark.skipif(
    not _RNSH_AVAILABLE,
    reason="RNS.Utilities.rnsh.rnsh is not installed",
)
@pytest.mark.skipif(sys.platform != "linux", reason="Landlock live check is Linux-only")
def test_rnsh_live_listen_under_landlock_with_storage_home():
    """Landlock on + HOME under storage: MeshChatX-style env lets rnsh listen."""
    import subprocess
    import sys
    from pathlib import Path

    from meshchatx.src.backend.landlock_sandbox import landlock_kernel_supported

    if not landlock_kernel_supported():
        pytest.skip("Landlock not available on this kernel")

    storage = tempfile.mkdtemp(prefix="meshchat_rnsh_ll_ok_storage_")
    rns_dir = tempfile.mkdtemp(prefix="meshchat_rnsh_ll_ok_rns_")
    _write_isolated_rns_config(rns_dir, port=_free_port(), name="rnsh_ll_ok")
    script = textwrap.dedent(
        f"""\
        import os
        import sys
        import time
        from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox
        from meshchatx.src.backend.rnsh_manager import RNSHSession

        storage = {storage!r}
        rns_dir = {rns_dir!r}
        os.environ["MESHCHAT_LANDLOCK"] = "1"
        ok = apply_landlock_sandbox(
            storage_dir=storage,
            reticulum_config_dir=rns_dir,
            log_dir=storage,
        )
        if not ok:
            print("LANDLOCK_NOT_APPLIED")
            sys.exit(2)

        class Manager:
            def __init__(self):
                self.storage_dir = storage
                self.reticulum_config_dir = rns_dir
            def _on_session_change(self, _s):
                return None
            def _on_session_output(self, _s, _c):
                return None
            def save(self):
                return None

        # Avoid PTY SIGHUP under capture.
        RNSHSession._supports_pty = staticmethod(lambda: False)
        session = RNSHSession(
            Manager(),
            "live-ll-ok",
            {{
                "mode": "listen",
                "no_auth": True,
                "quiet": 1,
                "config_path": rns_dir,
            }},
        )
        env = session._build_env()
        print("HOME", env.get("HOME"))
        if env.get("HOME") != os.path.join(storage, "rnsh_home"):
            print("BAD_HOME")
            sys.exit(4)
        started = session.start()
        print("STATUS", started.get("status"))
        print("PID", started.get("pid"))
        deadline = time.time() + 35.0
        while time.time() < deadline:
            if session.listen_address:
                print("LISTEN", session.listen_address)
                text = session.to_dict(include_output_tail=True).get("output_text") or ""
                if "Could not get or create rnsh configuration directory" in text:
                    print("CONFIG_DIR_CRITICAL")
                    session.stop()
                    sys.exit(5)
                session.stop()
                print("OK")
                sys.exit(0)
            if session.status == "failed":
                print("FAILED", session.last_error)
                print("OUT", session.to_dict(include_output_tail=True).get("output_text"))
                sys.exit(6)
            time.sleep(0.2)
        print("TIMEOUT", session.to_dict(include_output_tail=True).get("output_text"))
        session.stop()
        sys.exit(7)
        """,
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if "LANDLOCK_NOT_APPLIED" in result.stdout:
            pytest.skip("Landlock could not be applied in this environment")
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert "OK" in result.stdout
        assert "LISTEN" in result.stdout
    finally:
        shutil.rmtree(storage, ignore_errors=True)
        shutil.rmtree(rns_dir, ignore_errors=True)
