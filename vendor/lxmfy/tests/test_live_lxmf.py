"""Live LXMF roundtrip over random online public TCP/backbone nodes.

Fetches online nodes from https://directory.rns.recipes, picks reachable
TCP/backbone entrypoints at random, connects two LXMFy bots through them,
and requires a ping/pong roundtrip.

Requires network access and LXMFY_LIVE_LXMF=1. Skips otherwise.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import random
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

DIRECTORY_URL = (
    "https://directory.rns.recipes/api/directory/submitted?search=&type=&status=online"
)
LIVE_ENABLED = os.environ.get("LXMFY_LIVE_LXMF", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
NODE_TYPES = {"tcp", "backbone"}
CONNECT_TRIES = int(os.environ.get("LXMFY_LIVE_LXMF_TRIES", "4"))
PATH_TIMEOUT_S = int(os.environ.get("LXMFY_LIVE_LXMF_PATH_TIMEOUT", "60"))
ROUNDTRIP_TIMEOUT_S = int(os.environ.get("LXMFY_LIVE_LXMF_ROUNDTRIP_TIMEOUT", "90"))


def _log(msg: str) -> None:
    print(msg, flush=True)


def _fetch_online_nodes(url: str = DIRECTORY_URL) -> list[dict]:
    with urllib.request.urlopen(url, timeout=30) as resp:
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
        if str(row.get("type", "")).lower() not in NODE_TYPES:
            continue
        if not row.get("host") or not row.get("port"):
            continue
        # Prefer clearnet TCP host:port targets for live CI hosts.
        host = str(row["host"])
        if ":" in host and not host.replace(":", "").isdigit():
            # Skip Yggdrasil / IPv6-literal-only style hosts unless bracketed.
            if host.count(":") > 1 and not host.startswith("["):
                continue
        nodes.append(row)
    return nodes


def _tcp_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _pick_reachable_nodes(nodes: list[dict], limit: int = CONNECT_TRIES) -> list[dict]:
    tcp_first = [n for n in nodes if str(n.get("type", "")).lower() == "tcp"]
    backbone = [n for n in nodes if str(n.get("type", "")).lower() == "backbone"]
    random.shuffle(tcp_first)
    random.shuffle(backbone)
    chosen: list[dict] = []
    for node in tcp_first + backbone:
        host = str(node["host"])
        port = int(node["port"])
        ok = _tcp_reachable(host, port)
        _log(f"probe {node.get('name')} {host}:{port} -> {ok}")
        if ok:
            chosen.append(node)
            if len(chosen) >= limit:
                break
    return chosen


def _interface_block(node: dict) -> str:
    raw = node.get("config")
    if isinstance(raw, str) and "type =" in raw:
        return raw.strip() + "\n"
    name = str(node.get("name") or "LiveNode").replace("]", "")
    host = node["host"]
    port = int(node["port"])
    ntype = str(node.get("type", "tcp")).lower()
    if ntype == "backbone":
        return (
            f"[[{name}]]\n"
            f"  type = BackboneInterface\n"
            f"  enabled = Yes\n"
            f"  remote = {host}\n"
            f"  target_port = {port}\n"
        )
    return (
        f"[[{name}]]\n"
        f"  type = TCPClientInterface\n"
        f"  enabled = Yes\n"
        f"  target_host = {host}\n"
        f"  target_port = {port}\n"
    )


def _write_rns_config(path: Path, node: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "config").write_text(
        "[reticulum]\n"
        "enable_transport = No\n"
        "share_instance = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        f"{_interface_block(node)}",
        encoding="utf-8",
    )


def _drain_outbound(bot) -> None:
    while not bot.queue.empty():
        try:
            lxm = bot.queue.get(block=False)
        except Exception:
            break
        try:
            if bot.router:
                bot.router.handle_outbound(lxm)
        except Exception as e:
            _log(f"outbound error: {e}")


def _bot_worker(
    role: str,
    config_dir: str,
    peer_hash_hex: str | None,
    peer_pub_hex: str | None,
    ready_q: multiprocessing.Queue,
    result_q: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
) -> None:
    import RNS
    from LXMF import LXMessage

    from lxmfy import BotConfig, LXMFBot

    os.environ.pop("LXMFY_RETICULUM_CONFIG_DIR", None)
    try:
        _log(f"{role}: starting in {config_dir}")
        bot = LXMFBot(
            **BotConfig(
                name=f"Live{role}",
                config_path=config_dir,
                reticulum_config_dir=config_dir,
                storage_path=str(Path(config_dir) / "storage"),
                announce_enabled=True,
                announce_immediately=True,
                first_message_enabled=False,
                landlock_enabled=False,
                cogs_enabled=False,
                message_persistence_enabled=False,
                propagation_fallback_enabled=False,
                test_mode=False,
            ).__dict__,
        )

        received: list[str] = []
        delivery_events: list[str] = []

        @bot.on_message()
        def on_msg(sender, message):
            raw = message.content
            content = raw.decode("utf-8") if isinstance(raw, bytes) else (raw or "")
            received.append(content)
            _log(f"{role}: recv {content!r} from {sender}")
            if role == "pong" and content:
                bot.send(
                    sender,
                    f"pong:{content}",
                    title="",
                    method=LXMessage.OPPORTUNISTIC,
                )
                _drain_outbound(bot)
            return True

        assert bot.local is not None
        local_hash = RNS.hexrep(bot.local.hash, delimit=False)
        local_pub = bot.identity.get_public_key().hex()
        ready_q.put((role, local_hash, local_pub))
        bot.announce_now(force=True)
        _drain_outbound(bot)

        if peer_hash_hex and peer_pub_hex:
            peer = bytes.fromhex(peer_hash_hex)
            RNS.Identity.remember(
                RNS.Identity.full_hash(peer),
                peer,
                bytes.fromhex(peer_pub_hex),
            )

        if role == "ping":
            peer = bytes.fromhex(peer_hash_hex or "")
            deadline = time.time() + PATH_TIMEOUT_S
            while time.time() < deadline and not stop_event.is_set():
                if RNS.Transport.has_path(peer) and RNS.Identity.recall(peer):
                    break
                RNS.Transport.request_path(peer)
                if int(time.time()) % 5 == 0:
                    bot.announce_now(force=True)
                _drain_outbound(bot)
                time.sleep(0.5)
            if not (RNS.Transport.has_path(peer) and RNS.Identity.recall(peer)):
                result_q.put(
                    (
                        role,
                        "no_identity_or_path",
                        {
                            "has_path": RNS.Transport.has_path(peer),
                            "identity": RNS.Identity.recall(peer) is not None,
                        },
                    ),
                )
                return

            token = f"live-lxmf-{os.getpid()}-{int(time.time())}"
            _log(f"{role}: path+identity ok, sending {token!r}")

            # Patch delivery callbacks onto the next queued LXMessage via send path.
            original_enqueue = bot._enqueue_outbound

            def enqueue_with_hooks(lxm):
                def ok(_m):
                    delivery_events.append("ok")

                def bad(_m):
                    delivery_events.append("fail")

                try:
                    lxm.register_delivery_callback(ok)
                    lxm.register_failed_callback(bad)
                except Exception:
                    pass
                return original_enqueue(lxm)

            bot._enqueue_outbound = enqueue_with_hooks
            if not bot.send(
                peer_hash_hex,
                token,
                title="",
                method=LXMessage.OPPORTUNISTIC,
            ):
                result_q.put((role, "send_failed", token))
                return
            # Keep pumping while LXMF retries opportunistic delivery.
            _drain_outbound(bot)

            wait_deadline = time.time() + ROUNDTRIP_TIMEOUT_S
            while time.time() < wait_deadline and not stop_event.is_set():
                _drain_outbound(bot)
                if any(m == f"pong:{token}" for m in received):
                    result_q.put((role, "ok", token))
                    return
                time.sleep(0.2)
            result_q.put(
                (
                    role,
                    "timeout",
                    {"received": received[-5:], "delivery": delivery_events},
                ),
            )
        else:
            while not stop_event.is_set():
                if int(time.time()) % 8 == 0:
                    bot.announce_now(force=True)
                _drain_outbound(bot)
                time.sleep(0.5)
            result_q.put((role, "stopped", received[-5:]))
    except Exception as e:
        _log(f"{role}: error {e}")
        result_q.put((role, "error", str(e)))
    finally:
        try:
            import RNS

            RNS.Reticulum.exit_handler()
        except Exception:
            pass
        os._exit(0)


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="Set LXMFY_LIVE_LXMF=1 to run live LXMF mesh roundtrip",
)
def test_live_lxmf_ping_pong_random_directory_node(tmp_path):
    """Ping/pong two LXMFy bots through a random online public TCP/backbone node."""
    try:
        nodes = _fetch_online_nodes()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        pytest.skip(f"directory.rns.recipes unavailable: {e}")

    assert nodes, "no online tcp/backbone nodes in directory"
    _log(f"directory returned {len(nodes)} online tcp/backbone nodes")
    candidates = _pick_reachable_nodes(nodes, limit=CONNECT_TRIES)
    if not candidates:
        pytest.skip("no reachable online tcp/backbone nodes")

    last_error = None
    for node in candidates:
        _log(
            f"trying node {node.get('name')} "
            f"({node.get('type')} {node.get('host')}:{node.get('port')})",
        )
        ping_dir = tmp_path / f"ping_{node['id']}"
        pong_dir = tmp_path / f"pong_{node['id']}"
        _write_rns_config(ping_dir, node)
        _write_rns_config(pong_dir, node)

        ready_q: multiprocessing.Queue = multiprocessing.Queue()
        result_q: multiprocessing.Queue = multiprocessing.Queue()
        stop_event = multiprocessing.Event()

        pong = multiprocessing.Process(
            target=_bot_worker,
            args=("pong", str(pong_dir), None, None, ready_q, result_q, stop_event),
        )
        pong.start()

        pong_hash = pong_pub = None
        ready_deadline = time.time() + 60
        while time.time() < ready_deadline:
            if not ready_q.empty():
                role, value, pub = ready_q.get()
                if role == "pong":
                    pong_hash, pong_pub = value, pub
                    break
            if not pong.is_alive():
                break
            time.sleep(0.2)

        if not pong_hash or not pong_pub:
            stop_event.set()
            pong.terminate()
            pong.join(timeout=5)
            last_error = f"pong failed on {node.get('name')}"
            continue

        # Restart pong is already running without peer info; tell ping the peer.
        # Pong does not need ping identity to receive.
        ping = multiprocessing.Process(
            target=_bot_worker,
            args=(
                "ping",
                str(ping_dir),
                pong_hash,
                pong_pub,
                ready_q,
                result_q,
                stop_event,
            ),
        )
        ping.start()
        ping.join(timeout=PATH_TIMEOUT_S + ROUNDTRIP_TIMEOUT_S + 30)
        stop_event.set()
        pong.join(timeout=10)
        for proc in (ping, pong):
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=5)

        results = []
        while not result_q.empty():
            results.append(result_q.get())
        _log(f"results for {node.get('name')}: {results}")

        if any(r[0] == "ping" and r[1] == "ok" for r in results):
            _log(
                f"LIVE_LXMF_PROVED {node.get('name')} "
                f"{node.get('host')}:{node.get('port')} {results}",
            )
            return

        last_error = f"node={node.get('name')} results={results}"

    pytest.fail(
        f"live LXMF roundtrip failed after trying {len(candidates)} nodes: {last_error}",
    )


if __name__ == "__main__":
    if not LIVE_ENABLED:
        print("Set LXMFY_LIVE_LXMF=1", file=sys.stderr)
        raise SystemExit(2)
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        test_live_lxmf_ping_pong_random_directory_node(Path(td))
