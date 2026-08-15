# SPDX-License-Identifier: 0BSD
"""Live two-peer LXMF path finding over public TCP client interfaces.

Picks a reachable TCP node from directory.rns.recipes, falling back to the
home-config US-East host if the directory is empty. Two isolated RNS
clients announce lxmf.delivery and request a path through that node.

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

from tests.backend.support.test_temp_dir import subprocess_test_env

_RUN = (
    os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"
    or os.environ.get(
        "MESHCHAT_LIVE_VALIDATION",
    )
    == "1"
)

DIRECTORY_URL = "https://directory.rns.recipes/api/directory/submitted?status=online"
HOME_US_EAST = ("45.77.109.86", 4965, "RNS_Transport_US-East")
PATH_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_TCP_PATH_TIMEOUT", "70"))
CONNECT_TRIES = int(os.environ.get("MESHCHAT_LIVE_TCP_TRIES", "3"))


def _tcp_reachable(host: str, port: int, timeout: float = 4.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _fetch_recipe_tcp_nodes() -> list[tuple[str, int, str]]:
    with urllib.request.urlopen(DIRECTORY_URL, timeout=20) as resp:
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
        if str(row.get("type", "")).lower() != "tcp":
            continue
        host = row.get("host")
        port = row.get("port")
        if not host or not port:
            continue
        host = str(host)
        if host.count(":") > 1 and not host.startswith("["):
            continue
        name = str(row.get("name") or host)
        nodes.append((host, int(port), name))
    return nodes


def _pick_candidates() -> list[tuple[str, int, str]]:
    chosen: list[tuple[str, int, str]] = []
    try:
        recipes = _fetch_recipe_tcp_nodes()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        recipes = []
    random.shuffle(recipes)
    for host, port, name in recipes:
        if _tcp_reachable(host, port):
            chosen.append((host, port, name))
        if len(chosen) >= CONNECT_TRIES:
            break
    if HOME_US_EAST not in chosen and _tcp_reachable(HOME_US_EAST[0], HOME_US_EAST[1]):
        chosen.append(HOME_US_EAST)
    return chosen


def _write_client_config(config_dir: Path, host: str, port: int) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = No\n"
        "share_instance = No\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        "  [[LiveTCP]]\n"
        "    type = TCPClientInterface\n"
        "    enabled = Yes\n"
        f"    target_host = {host}\n"
        f"    target_port = {port}\n",
        encoding="utf-8",
    )


_PONG_SCRIPT = textwrap.dedent(
    """\
    import json, os, sys, time
    import RNS

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    stop_path = os.path.join(share_dir, "stop")
    ready_path = os.path.join(share_dir, "pong.json")
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    dest = RNS.Destination(
        identity, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery",
    )
    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump({"dest": dest.hash.hex(), "pub": identity.get_public_key().hex()}, handle)
    deadline = time.time() + timeout_s + 20
    while time.time() < deadline and not os.path.isfile(stop_path):
        dest.announce()
        time.sleep(4)
    RNS.exit(0)
    """
)

_PING_SCRIPT = textwrap.dedent(
    """\
    import json, os, sys, time
    import RNS

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    ready_path = os.path.join(share_dir, "pong.json")
    result_path = os.path.join(share_dir, "ping.json")
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    local = RNS.Destination(
        identity, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery",
    )
    deadline = time.time() + 30
    pong = None
    while time.time() < deadline:
        if os.path.isfile(ready_path):
            with open(ready_path, encoding="utf-8") as handle:
                pong = json.load(handle)
            if pong.get("dest"):
                break
        time.sleep(0.2)
    if not pong:
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "no_pong_hash"}, handle)
        RNS.exit(0)
        raise SystemExit(0)
    peer = bytes.fromhex(pong["dest"])
    RNS.Identity.remember(
        RNS.Identity.full_hash(peer),
        peer,
        bytes.fromhex(pong["pub"]),
    )
    local.announce()
    path_deadline = time.time() + timeout_s
    while time.time() < path_deadline:
        if RNS.Transport.has_path(peer) and RNS.Identity.recall(peer):
            break
        RNS.Transport.request_path(peer)
        local.announce()
        time.sleep(0.5)
    identity_hash = identity.hash
    delivery_hash = local.hash
    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "ok": bool(RNS.Transport.has_path(peer) and RNS.Identity.recall(peer)),
                "has_path": bool(RNS.Transport.has_path(peer)),
                "recalled": RNS.Identity.recall(peer) is not None,
                "identity_is_delivery": identity_hash == delivery_hash,
                "peer": pong["dest"],
            },
            handle,
        )
    RNS.exit(0)
    """
)


def _run_pair(tmp_path: Path, host: str, port: int, name: str) -> dict:
    ping_dir = tmp_path / f"ping_{port}"
    pong_dir = tmp_path / f"pong_{port}"
    share_dir = tmp_path / f"share_{port}"
    share_dir.mkdir(parents=True, exist_ok=True)
    _write_client_config(ping_dir, host, port)
    _write_client_config(pong_dir, host, port)
    env = subprocess_test_env()
    pong = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _PONG_SCRIPT,
            str(pong_dir),
            str(share_dir),
            str(PATH_TIMEOUT_S),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ping = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _PING_SCRIPT,
            str(ping_dir),
            str(share_dir),
            str(PATH_TIMEOUT_S),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ping.wait(timeout=PATH_TIMEOUT_S + 45)
    except subprocess.TimeoutExpired:
        ping.kill()
    (share_dir / "stop").write_text("1", encoding="utf-8")
    try:
        pong.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pong.kill()
    result_path = share_dir / "ping.json"
    payload = {
        "ok": False,
        "reason": "no_result_file",
        "node": name,
        "host": host,
        "port": port,
    }
    if result_path.is_file():
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["node"] = name
        payload["host"] = host
        payload["port"] = port
    payload["ping_return"] = ping.returncode
    payload["pong_return"] = pong.returncode
    if ping.returncode not in (0, None):
        payload["ping_stderr"] = (ping.stderr.read() if ping.stderr else "")[-800:]
    return payload


@pytest.mark.integration
@pytest.mark.skipif(
    not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1 for live TCP path test"
)
def test_live_two_peer_path_over_random_tcp(tmp_path):
    candidates = _pick_candidates()
    if not candidates:
        pytest.skip("no reachable public TCP nodes")

    last = None
    for host, port, name in candidates:
        last = _run_pair(tmp_path, host, port, name)
        print(f"live tcp path {name} {host}:{port} -> {last}", flush=True)
        if last.get("ok") is True:
            assert last.get("identity_is_delivery") is False
            print(
                f"LXMF_LIVE_TCP_PATH_PROVED {name} {host}:{port}",
                flush=True,
            )
            return

    pytest.fail(
        f"no path between two new LXMF dests after {len(candidates)} TCP nodes: {last}"
    )
