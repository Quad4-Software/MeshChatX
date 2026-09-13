# SPDX-License-Identifier: 0BSD
"""Live Mesh Server image upload, routing, and download over Reticulum.

Starts a local RNS TCP transport and a Python PageNode, uploads a WebP
image, serves a Micron page that links to the image, and downloads both
the page and the image with NomadnetPageDownloader / NomadnetFileDownloader.

Enable with MESHCHAT_LIVE_NOMAD_IMAGE=1 or MESHCHAT_LIVE_VALIDATION=1.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests.backend.support.test_temp_dir import REPO_ROOT, subprocess_test_env

_RUN = (
    os.environ.get("MESHCHAT_LIVE_NOMAD_IMAGE") == "1"
    or os.environ.get("MESHCHAT_LIVE_VALIDATION") == "1"
)

PATH_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_TCP_PATH_TIMEOUT", "70"))
LINK_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_NOMAD_LINK_TIMEOUT", "30"))


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _write_tcp_pair(listen_dir: Path, conn_dir: Path, port: int) -> None:
    listen_cfg = textwrap.dedent(
        f"""\
        [reticulum]
          enable_transport = Yes
          share_instance = No
          shared_instance_port = {37000 + (port % 1000)}
          instance_name = nomad_img_listen_{port}
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
          enable_transport = No
          share_instance = No
          shared_instance_port = {38000 + (port % 1000)}
          instance_name = nomad_img_conn_{port}
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
    listen_dir.mkdir(parents=True, exist_ok=True)
    conn_dir.mkdir(parents=True, exist_ok=True)
    (listen_dir / "config").write_text(listen_cfg, encoding="utf-8")
    (conn_dir / "config").write_text(conn_cfg, encoding="utf-8")


def _minimal_webp() -> bytes:
    """Return a tiny but magic-valid WebP byte string."""
    webp_fourcc = b"WEBP"
    chunk_fourcc = b"VP8 "
    chunk_payload = b"\x00" * 8
    chunk_size = len(chunk_fourcc) + len(chunk_payload)
    file_size = len(webp_fourcc) + chunk_size
    return (
        b"RIFF"
        + file_size.to_bytes(4, "little")
        + webp_fourcc
        + chunk_fourcc
        + chunk_size.to_bytes(4, "little")
        + chunk_payload
    )


_WEBP_BYTES = _minimal_webp()

_PAGE_CONTENT = (
    b"`[Live image`:/file/test.webp`img=1;w=100;h=100;s=8]\n"
    b"This page was served over a real network\n"
)

_SERVER_SCRIPT = textwrap.dedent(
    f"""\
    import json, os, sys, time
    import RNS
    from meshchatx.src.backend.page_node import PageNode

    server_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    ready_path = os.path.join(share_dir, "server.json")
    stop_path = os.path.join(share_dir, "stop")
    data_dir = os.path.join(share_dir, "node")

    RNS.Reticulum(configdir=server_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    node = PageNode(
        node_id="live-image-server",
        name="Live Image Server",
        base_dir=data_dir,
        identity=identity,
        announce_enabled=True,
    )
    node.setup()
    node.add_file("test.webp", {_WEBP_BYTES!r})
    node.add_page("index.mu", {_PAGE_CONTENT!r})

    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump({{"dest": node.destination.hash.hex()}}, handle)

    deadline = time.time() + timeout_s + 30
    while time.time() < deadline and not os.path.isfile(stop_path):
        node.announce()
        time.sleep(4)
    RNS.exit(0)
    """,
)

_CLIENT_SCRIPT = textwrap.dedent(
    f"""\
    import asyncio, json, os, sys, time
    import RNS
    from meshchatx.src.backend.nomadnet_downloader import (
        NomadnetFileDownloader,
        NomadnetPageDownloader,
    )

    client_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    LINK_TIMEOUT_S = 30
    ready_path = os.path.join(share_dir, "server.json")
    result_path = os.path.join(share_dir, "client.json")

    RNS.Reticulum(configdir=client_dir, loglevel=RNS.LOG_ERROR)

    deadline = time.time() + 30
    while not os.path.isfile(ready_path) and time.time() < deadline:
        time.sleep(0.2)

    if not os.path.isfile(ready_path):
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({{"ok": False, "reason": "server never became ready"}}, handle)
        RNS.exit(0)

    with open(ready_path, "r", encoding="utf-8") as handle:
        server = json.load(handle)
    dest_hash = bytes.fromhex(server["dest"])

    state = {{
        "result": {{
            "ok": False,
            "reason": "timeout",
            "page": None,
            "file_name": None,
            "file_bytes_b64": None,
        }},
        "page_text": None,
        "image_bytes": None,
        "image_file_name": None,
        "done": False,
        "file_done": False,
    }}

    def page_success(text):
        state["page_text"] = str(text)
        state["done"] = True

    def page_failure(reason):
        state["result"]["reason"] = f"page_failed: {{reason}}"
        state["done"] = True

    async def download_page():
        downloader = NomadnetPageDownloader(
            dest_hash,
            "/page/index.mu",
            None,
            page_success,
            page_failure,
            lambda p: None,
            timeout=int(timeout_s),
        )
        await downloader.download(
            path_lookup_timeout=timeout_s,
            link_establishment_timeout=LINK_TIMEOUT_S,
        )

    try:
        asyncio.run(download_page())
    except Exception as e:
        state["result"]["reason"] = f"page_exception: {{e}}"
        state["done"] = True

    wait_deadline = time.time() + timeout_s + 20
    while not state["done"] and time.time() < wait_deadline:
        time.sleep(0.2)

    if state["page_text"] is None:
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump(state["result"], handle)
        RNS.exit(0)

    state["result"]["page"] = state["page_text"]
    state["result"]["page_contains_image"] = (
        "/file/test.webp" in state["page_text"] and "img=1" in state["page_text"]
    )

    def file_success(name, data):
        state["image_file_name"] = name
        state["image_bytes"] = data
        state["file_done"] = True

    def file_failure(reason):
        state["result"]["reason"] = f"file_failed: {{reason}}"
        state["file_done"] = True

    async def download_file():
        downloader = NomadnetFileDownloader(
            dest_hash,
            "/file/test.webp",
            file_success,
            file_failure,
            lambda p: None,
            timeout=int(timeout_s),
        )
        await downloader.download(
            path_lookup_timeout=timeout_s,
            link_establishment_timeout=LINK_TIMEOUT_S,
        )

    try:
        asyncio.run(download_file())
    except Exception as e:
        state["result"]["reason"] = f"file_exception: {{e}}"
        state["file_done"] = True

    wait_deadline = time.time() + timeout_s + 20
    while not state["file_done"] and time.time() < wait_deadline:
        time.sleep(0.2)

    if state["image_bytes"] is not None:
        import base64

        state["result"]["ok"] = True
        state["result"]["reason"] = "ok"
        state["result"]["file_name"] = state["image_file_name"]
        state["result"]["file_bytes_b64"] = base64.b64encode(state["image_bytes"]).decode("utf-8")
        state["result"]["file_matches"] = state["image_bytes"] == {_WEBP_BYTES!r}

    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(state["result"], handle)

    RNS.exit(0)
    """,
)


def _run_pair(tmp_path: Path, port: int) -> dict:
    server_dir = tmp_path / f"listen_{port}"
    client_dir = tmp_path / f"conn_{port}"
    share_dir = tmp_path / f"share_{port}"
    share_dir.mkdir(parents=True, exist_ok=True)
    _write_tcp_pair(server_dir, client_dir, port)
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
    }
    if result_path.is_file():
        payload = json.loads(result_path.read_text(encoding="utf-8"))
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
    reason="Set MESHCHAT_LIVE_NOMAD_IMAGE=1 or MESHCHAT_LIVE_VALIDATION=1",
)
def test_live_mesh_server_webp_image_upload_and_download(tmp_path: Path):
    port = _free_port()
    result = _run_pair(tmp_path, port)
    print(f"live mesh server image result: {result}", flush=True)
    assert result.get("ok") is True, result
    assert result.get("page_contains_image") is True, result
    assert result.get("file_name") == "test.webp", result
    assert result.get("file_matches") is True, result
