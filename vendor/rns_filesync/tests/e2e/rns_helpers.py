"""Multi-process Reticulum peer helpers for e2e and live tests."""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import socket
import textwrap
import time
from pathlib import Path


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def write_config(
    config_dir: Path,
    *,
    name: str,
    listen_port: int | None,
    peer_port: int | None,
    shared_port: int | None = None,
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "storage").mkdir(exist_ok=True)
    interfaces = []
    if listen_port is not None:
        interfaces.append(
            textwrap.dedent(
                f"""
                [[TCP Server {name}]]
                  type = TCPServerInterface
                  enabled = yes
                  listen_ip = 127.0.0.1
                  listen_port = {listen_port}
                """,
            ).strip(),
        )
    if peer_port is not None:
        interfaces.append(
            textwrap.dedent(
                f"""
                [[TCP Client {name}]]
                  type = TCPClientInterface
                  enabled = yes
                  target_host = 127.0.0.1
                  target_port = {peer_port}
                """,
            ).strip(),
        )
    if shared_port is None:
        shared_port = free_port()
    config = (
        textwrap.dedent(
            f"""
        [reticulum]
          enable_transport = Yes
          share_instance = No
          shared_instance_port = {shared_port}
          instance_name = filesync_{name}_{listen_port or peer_port}_{shared_port}
          panic_on_interface_error = No

        [logging]
          loglevel = 5

        [interfaces]
        {chr(10).join(interfaces)}
        """,
        ).strip()
        + "\n"
    )
    (config_dir / "config").write_text(config)


def wait_until(predicate, timeout: float = 30.0, interval: float = 0.25) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def _peer_worker(config_dir: str, sync_dir: str, ready_q, cmd_q, result_q) -> None:
    """Generic FileSync peer process with command queue control."""
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
    ready_q.put(
        {
            "ok": True,
            "identity": identity.hash.hex(),
            "destination": dest,
        },
    )
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
        if cmd.get("op") == "connect":
            targets = list(cmd.get("targets") or [])
            connected = {"ok": False}
            deadline = time.time() + float(cmd.get("timeout", 60.0))
            while time.time() < deadline and not connected.get("ok"):
                for target in targets:
                    connected = service.connect_peer(target, timeout=8.0)
                    if connected.get("ok"):
                        break
                if not connected.get("ok"):
                    time.sleep(1.0)
            result_q.put({"ok": bool(connected.get("ok")), "connected": connected})
        elif cmd.get("op") == "write":
            path = os.path.join(sync_dir, cmd["path"])
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(cmd["data"])
            service.inventory.scan()
            service.inventory.save()
            if cmd.get("broadcast"):
                service._broadcast_update(cmd["path"])
            result_q.put({"ok": True, "op": "write"})
        elif cmd.get("op") == "delete":
            path = os.path.join(sync_dir, cmd["path"])
            if os.path.exists(path):
                os.remove(path)
            service._monitor_once()
            result_q.put({"ok": True, "op": "delete"})
        elif cmd.get("op") == "scan":
            service.inventory.scan()
            service.inventory.save()
            result_q.put({"ok": True, "op": "scan"})
        elif cmd.get("op") == "announce":
            service.announce_now()
            result_q.put({"ok": True, "op": "announce"})
        elif cmd.get("op") == "status":
            result_q.put(
                {
                    "ok": True,
                    "status": service.get_status(),
                    "files": service.list_files(),
                    "peers": service.list_peers(),
                },
            )


def _peer_b_main(config_dir: str, sync_dir: str, ready_q, cmd_q, result_q) -> None:
    _peer_worker(config_dir, sync_dir, ready_q, cmd_q, result_q)


def _peer_a_main(
    config_dir: str,
    sync_dir: str,
    peer_identity_hex: str,
    peer_destination_hex: str,
    ready_q,
    cmd_q,
    result_q,
) -> None:
    """Legacy two-peer client: connect once then idle on commands."""
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
    targets = [peer_identity_hex, peer_destination_hex]
    deadline = time.time() + 60.0
    while time.time() < deadline and not connected.get("ok"):
        for target in targets:
            connected = service.connect_peer(target, timeout=8.0)
            if connected.get("ok"):
                break
        if not connected.get("ok"):
            time.sleep(1.0)
    ready_q.put({"connected": connected, "identity": identity.hash.hex()})
    while True:
        cmd = cmd_q.get()
        if cmd is None or cmd.get("op") == "stop":
            service.stop()
            result_q.put({"stopped": True})
            break
        if cmd.get("op") == "status":
            result_q.put(
                {"status": service.get_status(), "files": service.list_files()},
            )


class _PeerHandle:
    def __init__(
        self, name: str, root: Path, *, listen_port: int | None, peer_port: int | None
    ):
        self.name = name
        self.dir = root / name
        self.cfg = root / f"cfg_{name}"
        self.dir.mkdir()
        write_config(
            self.cfg,
            name=name,
            listen_port=listen_port,
            peer_port=peer_port,
        )
        ctx = mp.get_context("spawn")
        self.ready = ctx.Queue()
        self.cmd = ctx.Queue()
        self.res = ctx.Queue()
        self.proc = None
        self.identity = None
        self.destination = None

    def start(self) -> None:
        ctx = mp.get_context("spawn")
        self.proc = ctx.Process(
            target=_peer_worker,
            args=(str(self.cfg), str(self.dir), self.ready, self.cmd, self.res),
            daemon=True,
        )
        self.proc.start()
        info = self.ready.get(timeout=45)
        if not info.get("ok", True):
            raise RuntimeError(f"peer {self.name} failed to start: {info}")
        self.identity = info["identity"]
        self.destination = info["destination"]

    def connect(self, *targets: str, timeout: float = 60.0) -> dict:
        self.cmd.put({"op": "connect", "targets": list(targets), "timeout": timeout})
        result = self.res.get(timeout=timeout + 30.0)
        if not result.get("ok"):
            raise RuntimeError(f"peer {self.name} connect failed: {result}")
        return result

    def write(self, relpath: str, data: bytes, broadcast: bool = False) -> None:
        self.cmd.put(
            {"op": "write", "path": relpath, "data": data, "broadcast": broadcast},
        )
        assert self.res.get(timeout=30).get("ok")

    def delete(self, relpath: str) -> None:
        self.cmd.put({"op": "delete", "path": relpath})
        assert self.res.get(timeout=30).get("ok")

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            self.cmd.put({"op": "stop"})
            self.res.get(timeout=10)
        except Exception:
            pass
        self.proc.join(timeout=5)
        if self.proc.is_alive():
            self.proc.terminate()


class TwoPeerHarness:
    """Manage two FileSync peers in separate processes over TCP."""

    def __init__(self, root: Path):
        self.root = root
        self.port = free_port()
        self.dir_a = root / "a"
        self.dir_b = root / "b"
        self.cfg_a = root / "cfg_a"
        self.cfg_b = root / "cfg_b"
        self.dir_a.mkdir()
        self.dir_b.mkdir()
        write_config(self.cfg_b, name="b", listen_port=self.port, peer_port=None)
        write_config(self.cfg_a, name="a", listen_port=None, peer_port=self.port)

        ctx = mp.get_context("spawn")
        self.ready_b = ctx.Queue()
        self.cmd_b = ctx.Queue()
        self.res_b = ctx.Queue()
        self.ready_a = ctx.Queue()
        self.cmd_a = ctx.Queue()
        self.res_a = ctx.Queue()
        self.proc_b = None
        self.proc_a = None
        self.peer_b_identity = None
        self.peer_b_destination = None

    def start(self) -> None:
        ctx = mp.get_context("spawn")
        self.proc_b = ctx.Process(
            target=_peer_b_main,
            args=(
                str(self.cfg_b),
                str(self.dir_b),
                self.ready_b,
                self.cmd_b,
                self.res_b,
            ),
            daemon=True,
        )
        self.proc_b.start()
        info = self.ready_b.get(timeout=30)
        self.peer_b_identity = info["identity"]
        self.peer_b_destination = info["destination"]
        time.sleep(0.8)

        self.proc_a = ctx.Process(
            target=_peer_a_main,
            args=(
                str(self.cfg_a),
                str(self.dir_a),
                self.peer_b_identity,
                self.peer_b_destination,
                self.ready_a,
                self.cmd_a,
                self.res_a,
            ),
            daemon=True,
        )
        self.proc_a.start()
        a_info = self.ready_a.get(timeout=90)
        if not a_info.get("connected", {}).get("ok"):
            raise RuntimeError(f"peer A failed to connect: {a_info}")

    def b_write(self, relpath: str, data: bytes, broadcast: bool = False) -> None:
        self.cmd_b.put(
            {"op": "write", "path": relpath, "data": data, "broadcast": broadcast},
        )
        assert self.res_b.get(timeout=30).get("ok")

    def b_delete(self, relpath: str) -> None:
        self.cmd_b.put({"op": "delete", "path": relpath})
        assert self.res_b.get(timeout=30).get("ok")

    def stop(self) -> None:
        for cmd, res, proc in (
            (self.cmd_a, self.res_a, self.proc_a),
            (self.cmd_b, self.res_b, self.proc_b),
        ):
            if proc is None:
                continue
            try:
                cmd.put({"op": "stop"})
                res.get(timeout=10)
            except Exception:
                pass
            proc.join(timeout=5)
            if proc.is_alive():
                proc.terminate()


class ThreePeerHarness:
    """Star topology: hub listens, two leaves connect over TCP.

    Verifies multi-peer links and hub fan-out (leaf write reaches the other leaf).
    """

    def __init__(self, root: Path):
        self.root = root
        self.port = free_port()
        self.hub = _PeerHandle("hub", root, listen_port=self.port, peer_port=None)
        self.leaf_a = _PeerHandle("leaf_a", root, listen_port=None, peer_port=self.port)
        self.leaf_b = _PeerHandle("leaf_b", root, listen_port=None, peer_port=self.port)

    @property
    def dir_hub(self) -> Path:
        return self.hub.dir

    @property
    def dir_a(self) -> Path:
        return self.leaf_a.dir

    @property
    def dir_b(self) -> Path:
        return self.leaf_b.dir

    def start(self) -> None:
        self.hub.start()
        time.sleep(0.8)
        self.leaf_a.start()
        self.leaf_a.connect(self.hub.identity, self.hub.destination, timeout=60.0)
        self.leaf_b.start()
        self.leaf_b.connect(self.hub.identity, self.hub.destination, timeout=60.0)
        time.sleep(0.5)

    def hub_write(self, relpath: str, data: bytes, broadcast: bool = False) -> None:
        self.hub.write(relpath, data, broadcast=broadcast)

    def leaf_a_write(self, relpath: str, data: bytes, broadcast: bool = False) -> None:
        self.leaf_a.write(relpath, data, broadcast=broadcast)

    def leaf_b_write(self, relpath: str, data: bytes, broadcast: bool = False) -> None:
        self.leaf_b.write(relpath, data, broadcast=broadcast)

    def stop(self) -> None:
        for peer in (self.leaf_a, self.leaf_b, self.hub):
            peer.stop()
