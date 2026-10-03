"""Live two-process LXMF exchange over a localhost UDP pair.

Unlike test_live_local_alice_bob.py (TCP loopback), this drives a real
UDPInterface pair and sends with LXMessage.DIRECT, which forces
link-based delivery and exercises the delivery-link callback chain that
wires packet and resource callbacks on inbound links. A regression
there stalls transfers mid-link, so this test would have caught it.

Requires LXMFY_LIVE_UDP=1. No public network needed.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

LIVE_ENABLED = os.environ.get("LXMFY_LIVE_UDP", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

READY_TIMEOUT_S = 60
RESULT_TIMEOUT_S = 90


def _free_udp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _write_udp_config(path: Path, listen_port: int, forward_port: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 4\n"
        "\n"
        "[interfaces]\n"
        "[[UDP]]\n"
        "  type = UDPInterface\n"
        "  enabled = Yes\n"
        "  listen_ip = 127.0.0.1\n"
        f"  listen_port = {listen_port}\n"
        "  forward_ip = 127.0.0.1\n"
        f"  forward_port = {forward_port}\n",
        encoding="utf-8",
    )


def _start(script: str, *args: str) -> subprocess.Popen:
    repo_root = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("LXMFY_RETICULUM_CONFIG_DIR", None)
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / script), *args],
        stdout=sys.stderr,
        stderr=sys.stderr,
        env=env,
    )


def _wait_file(path: Path, timeout_s: float, proc: subprocess.Popen) -> str | None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return path.read_text(encoding="utf-8").strip()
        if proc.poll() is not None:
            return None
        time.sleep(0.3)
    return None


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="Set LXMFY_LIVE_UDP=1 to run the localhost UDP pair test",
)
def test_udp_pair_command_attachment_and_replies(tmp_path):
    bot_port = _free_udp_port()
    client_port = _free_udp_port()

    bot_dir = tmp_path / "bot"
    client_dir = tmp_path / "client"
    _write_udp_config(bot_dir, listen_port=bot_port, forward_port=client_port)
    _write_udp_config(client_dir, listen_port=client_port, forward_port=bot_port)

    ready_file = tmp_path / "bot_ready"
    result_file = tmp_path / "result.json"

    bot = _start("live_udp_bot.py", str(bot_dir), str(ready_file))
    client = None
    try:
        bot_hash = _wait_file(ready_file, READY_TIMEOUT_S, bot)
        assert bot_hash, "bot never wrote its destination hash"

        client = _start(
            "live_udp_client.py",
            str(client_dir),
            bot_hash,
            str(result_file),
        )
        raw = _wait_file(result_file, RESULT_TIMEOUT_S, client)
        assert raw, "client never wrote a result"
        result = json.loads(raw)

        assert result["error"] is None
        assert result["pong"], "no pong reply for /ping command"
        assert result["pong"]["signature_validated"] is True
        assert result["file_ack"], "no acknowledgement for file attachment"
    finally:
        for proc in (client, bot):
            if proc is not None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
