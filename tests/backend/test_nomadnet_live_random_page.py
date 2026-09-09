# SPDX-License-Identifier: 0BSD
"""Live NomadNet page download over a public Reticulum TCP/Backbone node.

Starts two isolated RNS peers, has one announce a nomadnetwork.node
page destination, and downloads /index.mu through the actual
NomadnetPageDownloader over the public network.

Enable with MESHCHAT_LIVE_RETICULUM=1 or MESHCHAT_LIVE_VALIDATION=1.
"""

from __future__ import annotations

import json
import os
import random
import socket
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tests.backend.support.test_temp_dir import REPO_ROOT, subprocess_test_env

_RUN = (
    os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"
    or os.environ.get("MESHCHAT_LIVE_VALIDATION") == "1"
)

DIRECTORY_URL = "https://directory.rns.recipes/api/directory/submitted?status=online"
HOME_US_EAST = ("tcp", "45.77.109.86", 4965, "RNS_Transport_US-East")
PATH_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_TCP_PATH_TIMEOUT", "70"))
LINK_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_NOMAD_LINK_TIMEOUT", "30"))


def _tcp_reachable(host: str, port: int, timeout: float = 4.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _fetch_recipe_nodes() -> list[tuple[str, str, int, str]]:
    with urllib.request.urlopen(DIRECTORY_URL, timeout=20) as resp:  # nosec: BAN-B310
        payload = json.loads(resp.read().decode("utf-8"))
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    nodes = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).lower() != "online":
            continue
        node_type = str(row.get("type", "")).lower()
        if node_type not in ("tcp", "backbone"):
            continue
        host = row.get("host")
        port = row.get("port")
        if not host or not port:
            continue
        host = str(host)
        if host.count(":") > 1 and not host.startswith("["):
            continue
        name = str(row.get("name") or host)
        nodes.append((node_type, host, int(port), name))
    return nodes


def _pick_candidates() -> list[tuple[str, str, int, str]]:
    chosen: list[tuple[str, str, int, str]] = []
    try:
        recipes = _fetch_recipe_nodes()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        recipes = []
    random.shuffle(recipes)
    for node_type, host, port, name in recipes:
        if _tcp_reachable(host, port):
            chosen.append((node_type, host, port, name))
        if len(chosen) >= 3:
            break
    if HOME_US_EAST not in chosen and _tcp_reachable(HOME_US_EAST[1], HOME_US_EAST[2]):
        chosen.append(HOME_US_EAST)
    return chosen


def _write_client_config(
    config_dir: Path, node_type: str, host: str, port: int
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    if node_type == "tcp":
        iface = (
            "  [[LiveTCP]]\n"
            "    type = TCPClientInterface\n"
            "    enabled = Yes\n"
            f"    target_host = {host}\n"
            f"    target_port = {port}\n"
        )
    else:
        iface = (
            "  [[LiveBackbone]]\n"
            "    type = BackboneInterface\n"
            "    enabled = Yes\n"
            f"    remote = {host}\n"
            f"    target_port = {port}\n"
        )
    (config_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = No\n"
        "share_instance = No\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n" + iface,
        encoding="utf-8",
    )


_PAGE_CONTENT = b"# MeshChatX live page\nThis page was served over a real network\n"

_SERVER_SCRIPT = textwrap.dedent(
    """\
    import json, os, sys, time
    import RNS

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    ready_path = os.path.join(share_dir, "server.json")
    stop_path = os.path.join(share_dir, "stop")

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    dest = RNS.Destination(
        identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        "nomadnetwork",
        "node",
    )

    def responder(path, data, request_id, link_id, remote_identity, requested_at):
        if path == "/index.mu":
            return {page_content!r}
        return None

    dest.register_request_handler(
        "/index.mu",
        response_generator=responder,
        allow=RNS.Destination.ALLOW_ALL,
    )

    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump({{"dest": dest.hash.hex()}}, handle)

    deadline = time.time() + timeout_s + 20
    while time.time() < deadline and not os.path.isfile(stop_path):
        dest.announce(app_data=b"live-page")
        time.sleep(4)
    RNS.exit(0)
    """.format(page_content=_PAGE_CONTENT),
)

_CLIENT_SCRIPT = textwrap.dedent(
    """\
    import asyncio, json, os, sys, time
    import RNS
    from meshchatx.src.backend.nomadnet_downloader import NomadnetPageDownloader

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    ready_path = os.path.join(share_dir, "server.json")
    result_path = os.path.join(share_dir, "client.json")

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)

    deadline = time.time() + 30
    while not os.path.isfile(ready_path) and time.time() < deadline:
        time.sleep(0.2)

    if not os.path.isfile(ready_path):
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "server never became ready"}, handle)
        RNS.exit(0)

    with open(ready_path, "r", encoding="utf-8") as handle:
        server = json.load(handle)
    dest_hash = bytes.fromhex(server["dest"])

    result = {"ok": False, "reason": "timeout"}
    done = False

    def on_success(page_text):
        global result, done
        result = {"ok": True, "page": str(page_text)}
        done = True

    def on_failure(reason):
        global result, done
        result = {"ok": False, "reason": str(reason)}
        done = True

    async def run():
        downloader = NomadnetPageDownloader(
            dest_hash,
            "/index.mu",
            None,
            on_success,
            on_failure,
            lambda p: None,
            timeout=int(timeout_s),
        )
        await downloader.download(
            path_lookup_timeout=timeout_s,
            link_establishment_timeout=30,
        )

    try:
        asyncio.run(run())
    except Exception as e:
        result = {"ok": False, "reason": f"exception: {e}"}

    wait_deadline = time.time() + timeout_s + 20
    while not done and time.time() < wait_deadline:
        time.sleep(0.2)

    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle)

    RNS.exit(0)
    """,
)


def _run_pair(tmp_path: Path, node_type: str, host: str, port: int, name: str) -> dict:
    server_dir = tmp_path / f"server_{port}"
    client_dir = tmp_path / f"client_{port}"
    share_dir = tmp_path / f"share_{port}"
    share_dir.mkdir(parents=True, exist_ok=True)
    _write_client_config(server_dir, node_type, host, port)
    _write_client_config(client_dir, node_type, host, port)
    env = subprocess_test_env()
    env["PYTHONPATH"] = str(REPO_ROOT)

    server = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _SERVER_SCRIPT,
            str(server_dir),
            str(share_dir),
            str(PATH_TIMEOUT_S),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    client = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _CLIENT_SCRIPT,
            str(client_dir),
            str(share_dir),
            str(PATH_TIMEOUT_S),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        client.wait(timeout=PATH_TIMEOUT_S + 45)
    except subprocess.TimeoutExpired:
        client.kill()
    (share_dir / "stop").write_text("1", encoding="utf-8")
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()

    result_path = share_dir / "client.json"
    payload: dict = {
        "ok": False,
        "reason": "no_result_file",
        "node": name,
        "host": host,
        "port": port,
        "type": node_type,
    }
    if result_path.is_file():
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["node"] = name
        payload["host"] = host
        payload["port"] = port
        payload["type"] = node_type
    payload["client_return"] = client.returncode
    payload["server_return"] = server.returncode
    if client.returncode not in (0, None):
        payload["client_stderr"] = (client.stderr.read() if client.stderr else "")[
            -800:
        ]
    return payload


@pytest.mark.integration
@pytest.mark.skipif(
    not _RUN,
    reason="Set MESHCHAT_LIVE_RETICULUM=1 or MESHCHAT_LIVE_VALIDATION=1",
)
def test_live_nomadnet_page_download_over_random_interface(tmp_path: Path):
    candidates = _pick_candidates()
    if not candidates:
        pytest.skip("no reachable public TCP/Backbone nodes")

    last: dict | None = None
    for node_type, host, port, name in candidates:
        last = _run_pair(tmp_path, node_type, host, port, name)
        print(
            f"live nomadnet page {node_type} {name} {host}:{port} -> {last}", flush=True
        )
        if last.get("ok") is True:
            assert "This page was served over a real network" in last.get("page", "")
            print(
                f"NOMADNET_LIVE_PAGE_PROVED {node_type} {name} {host}:{port}",
                flush=True,
            )
            return

    pytest.fail(
        f"no nomadnetwork.node page downloaded after {len(candidates)} nodes: {last}"
    )
