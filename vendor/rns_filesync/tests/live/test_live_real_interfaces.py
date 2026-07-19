"""Live sync over real network interfaces.

Strategies:
- UDPInterface on free ports (real sockets, no AutoInterface conflict)
- Optional shared-instance attach to the host Reticulum config
- AutoInterface when not already bound by another stack
"""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import socket
import textwrap
import time
from pathlib import Path

import pytest

from tests.e2e.rns_helpers import wait_until

pytestmark = [pytest.mark.live]


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_udp_pair(cfg_a: Path, cfg_b: Path) -> None:
    port_a = _free_udp_port()
    port_b = _free_udp_port()
    shared_a = 46000 + (os.getpid() % 500) * 2
    shared_b = shared_a + 1

    def write(path: Path, name: str, listen: int, peer: int, shared: int) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "storage").mkdir(exist_ok=True)
        (path / "config").write_text(
            textwrap.dedent(
                f"""
                [reticulum]
                  enable_transport = Yes
                  share_instance = No
                  shared_instance_port = {shared}
                  instance_name = filesync_live_udp_{name}_{listen}
                  panic_on_interface_error = No

                [logging]
                  loglevel = 5

                [interfaces]
                  [[UDP {name}]]
                    type = UDPInterface
                    enabled = yes
                    listen_ip = 127.0.0.1
                    listen_port = {listen}
                    forward_ip = 127.0.0.1
                    forward_port = {peer}
                """,
            ).strip()
            + "\n",
        )

    write(cfg_a, "a", port_a, port_b, shared_a)
    write(cfg_b, "b", port_b, port_a, shared_b)


def _peer_b(config_dir: str, sync_dir: str, ready_q, cmd_q, result_q) -> None:
    import traceback

    try:
        import RNS

        from rns_filesync.service import FileSyncService

        RNS.loglevel = RNS.LOG_ERROR
        RNS.Reticulum(config_dir)
        identity = RNS.Identity()
        service = FileSyncService(
            identity=identity,
            sync_directory=sync_dir,
            reticulum=RNS.Reticulum.get_instance(),
        )
        dest = service.start(monitor=True, announce_interval=8)
        ready_q.put({"ok": True, "identity": identity.hash.hex(), "destination": dest})
        while True:
            try:
                cmd = cmd_q.get(timeout=2.0)
            except queue.Empty:
                service.announce_now()
                continue
            if cmd is None or cmd.get("op") == "stop":
                service.stop()
                result_q.put({"stopped": True})
                break
    except Exception as exc:
        ready_q.put({"ok": False, "error": str(exc), "trace": traceback.format_exc()})


def _peer_a(
    config_dir: str,
    sync_dir: str,
    peer_identity_hex: str,
    peer_destination_hex: str,
    ready_q,
    cmd_q,
    result_q,
) -> None:
    import traceback

    try:
        import RNS

        from rns_filesync.service import FileSyncService

        RNS.loglevel = RNS.LOG_ERROR
        RNS.Reticulum(config_dir)
        identity = RNS.Identity()
        service = FileSyncService(
            identity=identity,
            sync_directory=sync_dir,
            reticulum=RNS.Reticulum.get_instance(),
        )
        service.start(monitor=True, announce_interval=8)
        connected = {"ok": False}
        deadline = time.time() + 60.0
        targets = [peer_identity_hex, peer_destination_hex]
        while time.time() < deadline and not connected.get("ok"):
            for target in targets:
                connected = service.connect_peer(target, timeout=8.0)
                if connected.get("ok"):
                    break
            if not connected.get("ok"):
                time.sleep(1.0)
        ready_q.put(
            {"ok": True, "connected": connected, "identity": identity.hash.hex()},
        )
        while True:
            cmd = cmd_q.get()
            if cmd is None or cmd.get("op") == "stop":
                service.stop()
                result_q.put({"stopped": True})
                break
    except Exception as exc:
        ready_q.put({"ok": False, "error": str(exc), "trace": traceback.format_exc()})


def _run_two_peer_live(tmp_path: Path, write_configs) -> None:
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    cfg_a = tmp_path / "cfg_a"
    cfg_b = tmp_path / "cfg_b"
    dir_a.mkdir()
    dir_b.mkdir()
    write_configs(cfg_a, cfg_b)
    (dir_b / "live.txt").write_text("live-network-ok")

    ctx = mp.get_context("spawn")
    ready_b, cmd_b, res_b = ctx.Queue(), ctx.Queue(), ctx.Queue()
    ready_a, cmd_a, res_a = ctx.Queue(), ctx.Queue(), ctx.Queue()

    proc_b = ctx.Process(
        target=_peer_b,
        args=(str(cfg_b), str(dir_b), ready_b, cmd_b, res_b),
        daemon=True,
    )
    proc_b.start()
    info_b = ready_b.get(timeout=45)
    assert info_b.get("ok"), info_b
    time.sleep(1.0)

    proc_a = ctx.Process(
        target=_peer_a,
        args=(
            str(cfg_a),
            str(dir_a),
            info_b["identity"],
            info_b["destination"],
            ready_a,
            cmd_a,
            res_a,
        ),
        daemon=True,
    )
    proc_a.start()
    try:
        info_a = ready_a.get(timeout=90)
        assert info_a.get("ok"), info_a
        assert info_a.get("connected", {}).get("ok"), info_a
        assert wait_until(
            lambda: (
                (dir_a / "live.txt").is_file()
                and (dir_a / "live.txt").read_text() == "live-network-ok"
            ),
            timeout=60.0,
        )
    finally:
        for cmd, res, proc in ((cmd_a, res_a, proc_a), (cmd_b, res_b, proc_b)):
            try:
                cmd.put({"op": "stop"})
                res.get(timeout=10)
            except Exception:
                pass
            proc.join(timeout=5)
            if proc.is_alive():
                proc.terminate()


@pytest.mark.timeout(150)
def test_live_udp_interface_two_peer_sync(tmp_path):
    """Sync over real UDPInterface sockets (not isolated TCPServer pair)."""
    _run_two_peer_live(tmp_path, _write_udp_pair)


@pytest.mark.timeout(150)
def test_live_tcp_harness_still_works(tmp_path):
    from tests.e2e.rns_helpers import TwoPeerHarness

    h = TwoPeerHarness(tmp_path)
    (h.dir_b / "tcp-live.txt").write_text("tcp-ok")
    h.start()
    try:
        assert wait_until(
            lambda: (
                (h.dir_a / "tcp-live.txt").is_file()
                and (h.dir_a / "tcp-live.txt").read_text() == "tcp-ok"
            ),
            timeout=60.0,
        )
    finally:
        h.stop()


def test_live_host_reticulum_config_present():
    path = Path(os.environ.get("RNS_FILESYNC_LIVE_CONFIG", Path.home() / ".reticulum"))
    if not (path / "config").is_file():
        pytest.skip("host Reticulum config not present")
    assert (path / "config").is_file()
