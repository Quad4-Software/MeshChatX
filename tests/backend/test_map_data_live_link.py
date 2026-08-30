# SPDX-License-Identifier: 0BSD

"""Live map-data-v1 catalog fetch over an RNS Link on loopback TCP."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from tests.backend.eect.harness import eect_scenario
from tests.backend.support.test_temp_dir import subprocess_test_env

_PUB_SCRIPT = textwrap.dedent(
    r"""
    import json
    import os
    import sys
    import time

    import RNS

    from meshchatx.src.backend.database import Database
    from meshchatx.src.backend.map_data_manager import MapDataManager

    GEOJSON = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Camp"},
                    "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                },
            ],
        },
    ).encode()


    class FakeValue:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value


    class FakeConfig:
        def __init__(self):
            self.map_overlay_max_bytes = FakeValue(8 * 1024 * 1024)
            self.map_overlay_max_features = FakeValue(50_000)
            self.map_overlay_max_kmz_uncompressed_bytes = FakeValue(16 * 1024 * 1024)
            self.map_overlay_path_timeout_seconds = FakeValue(8)
            self.map_overlay_transfer_timeout_seconds = FakeValue(20)
            self.map_overlay_job_timeout_seconds = FakeValue(25)
            self.map_data_max_bytes = FakeValue(512 * 1024)
            self.map_data_announce_enabled = FakeValue(False)
            self.map_data_announce_interval = FakeValue(900)
            self.map_data_display_name = FakeValue("Camp maps")

    config_dir, share_dir = sys.argv[1], sys.argv[2]
    stop_path = os.path.join(share_dir, "stop")
    ready_path = os.path.join(share_dir, "ready.json")
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    db = Database(os.path.join(config_dir, "db.sqlite"))
    db.initialize()
    mgr = MapDataManager(
        FakeConfig(),
        db,
        os.path.join(config_dir, "store"),
        identity,
        reticulum=RNS.Reticulum.get_instance(),
    )
    mgr.start()
    if mgr._destination is not None:
        raise SystemExit("destination created before publish")
    published = mgr.publish_bytes(GEOJSON, name="Camp")
    if mgr._destination is None:
        raise SystemExit("destination missing after publish")
    mgr.announce()
    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "dest": mgr._destination.hash.hex(),
                "pub": identity.get_public_key().hex(),
                "map_id": published["map"]["map_id"],
            },
            handle,
        )
    deadline = time.time() + 45
    while time.time() < deadline and not os.path.isfile(stop_path):
        mgr.announce()
        time.sleep(1.5)
    RNS.exit(0)
    """,
)

_CLI_SCRIPT = textwrap.dedent(
    r"""
    import asyncio
    import json
    import os
    import sys
    import time

    import RNS

    from meshchatx.src.backend.database import Database
    from meshchatx.src.backend.map_data_manager import MapDataManager
    from meshchatx.src.backend.rns_link_manager import RnsLinkManager


    class FakeValue:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value


    class FakeConfig:
        def __init__(self):
            self.map_overlay_max_bytes = FakeValue(8 * 1024 * 1024)
            self.map_overlay_max_features = FakeValue(50_000)
            self.map_overlay_max_kmz_uncompressed_bytes = FakeValue(16 * 1024 * 1024)
            self.map_overlay_path_timeout_seconds = FakeValue(12)
            self.map_overlay_transfer_timeout_seconds = FakeValue(20)
            self.map_overlay_job_timeout_seconds = FakeValue(25)
            self.map_data_max_bytes = FakeValue(512 * 1024)
            self.map_data_announce_enabled = FakeValue(False)
            self.map_data_announce_interval = FakeValue(900)
            self.map_data_display_name = FakeValue("Client")

    config_dir, share_dir = sys.argv[1], sys.argv[2]
    ready_path = os.path.join(share_dir, "ready.json")
    result_path = os.path.join(share_dir, "result.json")
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    deadline = time.time() + 20
    ready = None
    while time.time() < deadline:
        if os.path.isfile(ready_path):
            with open(ready_path, encoding="utf-8") as handle:
                ready = json.load(handle)
            if ready.get("dest"):
                break
        time.sleep(0.2)
    if not ready:
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "no_ready"}, handle)
        RNS.exit(0)
        raise SystemExit(0)
    peer = bytes.fromhex(ready["dest"])
    RNS.Identity.remember(
        RNS.Identity.full_hash(peer),
        peer,
        bytes.fromhex(ready["pub"]),
    )
    path_deadline = time.time() + 20
    while time.time() < path_deadline:
        if RNS.Transport.has_path(peer) and RNS.Identity.recall(peer):
            break
        RNS.Transport.request_path(peer)
        time.sleep(0.4)
    db = Database(os.path.join(config_dir, "db.sqlite"))
    db.initialize()
    link_mgr = RnsLinkManager(
        self_identity_getter=lambda: identity,
        reticulum_getter=lambda: RNS.Reticulum.get_instance(),
        broadcast_event=lambda _payload: None,
    )
    mgr = MapDataManager(
        FakeConfig(),
        db,
        os.path.join(config_dir, "store"),
        identity,
        reticulum=RNS.Reticulum.get_instance(),
        link_manager_getter=lambda: link_mgr,
    )

    async def run():
        catalog = await mgr.fetch_catalog(peer.hex())
        maps = catalog.get("maps") or []
        if not maps:
            return {"ok": False, "reason": "empty_catalog", "catalog": catalog}
        body = await mgr.fetch_map_bytes(peer.hex(), maps[0]["id"])
        return {
            "ok": True,
            "name": maps[0]["name"],
            "map_id": maps[0]["id"],
            "published_id": ready["map_id"],
            "size": len(body),
            "has_path": bool(RNS.Transport.has_path(peer)),
        }

    try:
        payload = asyncio.run(run())
    except Exception as exc:
        payload = {"ok": False, "reason": str(exc)}
    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    RNS.exit(0)
    """,
)


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _write_pair(pub_dir: Path, cli_dir: Path, port: int) -> None:
    pub_dir.mkdir(parents=True, exist_ok=True)
    cli_dir.mkdir(parents=True, exist_ok=True)
    (pub_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        f"shared_instance_port = {37000 + (port % 1000)}\n"
        f"instance_name = map_data_pub_{port}\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        "  [[TCP Server]]\n"
        "    type = TCPServerInterface\n"
        "    enabled = Yes\n"
        "    listen_ip = 127.0.0.1\n"
        f"    listen_port = {port}\n",
        encoding="utf-8",
    )
    (cli_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        f"shared_instance_port = {38000 + (port % 1000)}\n"
        f"instance_name = map_data_cli_{port}\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        "  [[TCP Client]]\n"
        "    type = TCPClientInterface\n"
        "    enabled = Yes\n"
        "    target_host = 127.0.0.1\n"
        f"    target_port = {port}\n",
        encoding="utf-8",
    )


def test_live_catalog_and_map_bytes_over_rns_link(tmp_path):
    with eect_scenario("map.data.live_catalog_link"):
        port = _free_port()
        pub_dir = tmp_path / "pub"
        cli_dir = tmp_path / "cli"
        share_dir = tmp_path / "share"
        share_dir.mkdir(parents=True, exist_ok=True)
        _write_pair(pub_dir, cli_dir, port)
        env = subprocess_test_env()
        pub = subprocess.Popen(
            [sys.executable, "-c", _PUB_SCRIPT, str(pub_dir), str(share_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        cli = None
        try:
            ready = share_dir / "ready.json"
            deadline = time.time() + 25
            while time.time() < deadline and not ready.is_file():
                if pub.poll() is not None:
                    stdout, stderr = pub.communicate(timeout=5)
                    raise AssertionError(
                        f"publisher exited {pub.returncode}: {stderr}\n{stdout}",
                    )
                time.sleep(0.2)
            assert ready.is_file(), "publisher did not write ready.json"
            cli = subprocess.Popen(
                [sys.executable, "-c", _CLI_SCRIPT, str(cli_dir), str(share_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            result_path = share_dir / "result.json"
            deadline = time.time() + 40
            while time.time() < deadline and not result_path.is_file():
                if cli.poll() is not None and not result_path.is_file():
                    stdout, stderr = cli.communicate(timeout=5)
                    raise AssertionError(
                        f"client exited {cli.returncode}: {stderr}\n{stdout}",
                    )
                time.sleep(0.2)
            assert result_path.is_file(), "client did not write result.json"
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            assert payload.get("ok") is True, payload
            assert payload["name"] == "Camp"
            assert payload["map_id"] == payload["published_id"]
            assert payload["size"] > 0
        finally:
            (share_dir / "stop").write_text("1", encoding="utf-8")
            for proc in (cli, pub):
                if proc is None:
                    continue
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
