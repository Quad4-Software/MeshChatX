"""Live tests with full Reticulum instances over HTTPTunnelInterface.

Spawns isolated server and client shared instances in subprocesses, exchanges
traffic over the HTTP tunnel, and verifies a local program can attach to the
server shared instance via LocalInterface.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERFACE_SRC = REPO_ROOT / "HTTPInterface.py"
PEER_HELPER = Path(__file__).resolve().parent / "_live_rns_peer.py"


def free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def write_rns_config(
    configdir: Path,
    *,
    instance_name: str,
    shared_port: int,
    control_port: int,
    http_mode: str,
    listen_port: int | None = None,
    server_url: str | None = None,
):
    configdir.mkdir(parents=True, exist_ok=True)
    interfaces_dir = configdir / "interfaces"
    interfaces_dir.mkdir(exist_ok=True)
    shutil.copy2(INTERFACE_SRC, interfaces_dir / "HTTPInterface.py")

    if http_mode == "server":
        http_block = textwrap.dedent(
            f"""
            [[HTTP Tunnel]]
              type = HTTPInterface
              enabled = yes
              mode = server
              listen_host = 127.0.0.1
              listen_port = {listen_port}
              mtu = 4096
              poll_interval = 0.05
              check_user_agent = yes
            """
        )
    else:
        http_block = textwrap.dedent(
            f"""
            [[HTTP Tunnel]]
              type = HTTPInterface
              enabled = yes
              mode = client
              server_url = {server_url}
              mtu = 4096
              poll_interval = 0.05
            """
        )

    config = textwrap.dedent(
        f"""
        [reticulum]
          enable_transport = Yes
          share_instance = Yes
          instance_name = {instance_name}
          shared_instance_port = {shared_port}
          instance_control_port = {control_port}
          shared_instance_type = tcp

        [logging]
          loglevel = 3

        [interfaces]
          [[Default Interface]]
            type = AutoInterface
            enabled = No

        {http_block}
        """
    )
    (configdir / "config").write_text(config, encoding="utf-8")


def wait_file(path: Path, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return path.read_text(encoding="utf-8").strip()
        time.sleep(0.1)
    pytest.fail(f"timed out waiting for {path}")


def start_peer(args, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    # Ensure repo root is importable if needed
    full_env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + full_env.get("PYTHONPATH", "")
    return subprocess.Popen(
        [sys.executable, str(PEER_HELPER), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=full_env,
        cwd=str(REPO_ROOT),
    )


def terminate(proc: subprocess.Popen, timeout=8.0):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.fixture
def live_dirs(tmp_path):
    server_dir = tmp_path / "rns_server"
    client_dir = tmp_path / "rns_client"
    status_dir = tmp_path / "status"
    status_dir.mkdir()
    return server_dir, client_dir, status_dir


@pytest.mark.live
def test_live_rns_http_tunnel_link_and_local_client(live_dirs):
    server_dir, client_dir, status_dir = live_dirs
    http_port = free_tcp_port()
    server_shared = free_tcp_port()
    server_control = free_tcp_port()
    client_shared = free_tcp_port()
    client_control = free_tcp_port()

    write_rns_config(
        server_dir,
        instance_name="http-live-server",
        shared_port=server_shared,
        control_port=server_control,
        http_mode="server",
        listen_port=http_port,
    )
    write_rns_config(
        client_dir,
        instance_name="http-live-client",
        shared_port=client_shared,
        control_port=client_control,
        http_mode="client",
        server_url=f"http://127.0.0.1:{http_port}/",
    )

    server_announce = status_dir / "server_announce.hash"
    server_recv = status_dir / "server_recv.json"
    client_done = status_dir / "client_done.json"
    local_done = status_dir / "local_done.json"

    server_proc = start_peer(
        [
            "serve",
            "--configdir",
            str(server_dir),
            "--announce-file",
            str(server_announce),
            "--recv-file",
            str(server_recv),
        ]
    )
    try:
        dest_hash = wait_file(server_announce, timeout=45.0)

        # Allow HTTP listener to come up
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", http_port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            err = server_proc.stderr.read().decode("utf-8", errors="replace") if server_proc.stderr else ""
            pytest.fail(f"HTTP server port did not open\n{err}")

        client_proc = start_peer(
            [
                "client",
                "--configdir",
                str(client_dir),
                "--target-hash",
                dest_hash,
                "--done-file",
                str(client_done),
                "--payload",
                "live-http-rns-ok",
            ]
        )
        try:
            done_raw = wait_file(client_done, timeout=90.0)
            done = json.loads(done_raw)
            assert done.get("ok") is True, done

            recv_raw = wait_file(server_recv, timeout=30.0)
            recv = json.loads(recv_raw)
            assert recv.get("payload") == "live-http-rns-ok"

            # Local program attaches to the server shared instance
            local_proc = start_peer(
                [
                    "local_client",
                    "--configdir",
                    str(server_dir),
                    "--done-file",
                    str(local_done),
                    "--expect-hash",
                    dest_hash,
                ]
            )
            local = {}
            try:
                local_raw = wait_file(local_done, timeout=45.0)
                local = json.loads(local_raw)
                assert local.get("ok") is True, local
                assert local.get("connected_to_shared") is True
            finally:
                terminate(local_proc)
                out, err = local_proc.communicate(timeout=5)
                if not local.get("ok"):
                    pytest.fail(
                        "local client failed\n"
                        + out.decode("utf-8", errors="replace")
                        + err.decode("utf-8", errors="replace")
                    )
        finally:
            terminate(client_proc)
            cout, cerr = client_proc.communicate(timeout=5)
            if not client_done.is_file():
                pytest.fail(
                    "client peer failed\n"
                    + cout.decode("utf-8", errors="replace")
                    + cerr.decode("utf-8", errors="replace")
                )
    finally:
        terminate(server_proc)
        sout, serr = server_proc.communicate(timeout=5)
        if not server_announce.is_file():
            pytest.fail(
                "server peer failed\n"
                + sout.decode("utf-8", errors="replace")
                + serr.decode("utf-8", errors="replace")
            )
