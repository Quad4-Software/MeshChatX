# SPDX-License-Identifier: 0BSD

"""Live RRC hub daemon for the rrcd interoperability tests.

Runs a real RRC hub on its own Reticulum instance with a TCP server
interface, or an announce-only stub in zombie mode. Every envelope in
and out, link open and close, and periodic interface byte counters are
appended to JSONL files under the share directory so tests can assert
on real wire behaviour.

Usage:
    python rrcd.py <config_dir> <share_dir> <port> [options]

Options (positional):
    announce_interval  seconds between hub announces (default 60)
    rate_limit         advertised messages per minute (default 120)
    mode               hub | zombie (default hub)
    drop_msgs          1 to accept chat envelopes without relaying
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import threading
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.server import RRCServerManager

STATS_INTERVAL_S = 2.0
STOP_POLL_S = 0.2


class TrafficLog:
    """Append-only JSONL writer shared by the harness threads."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def write(self, row):
        with self._lock:
            try:
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, default=str) + "\n")
            except Exception:
                pass


def envelope_fields(data):
    """Summarize an encoded RRC envelope for the traffic log."""
    row = {"bytes": len(data)}
    try:
        env = proto.decode(data)
    except Exception:
        return row
    if not isinstance(env, dict):
        return row
    mid = env.get(proto.K_ID)
    src = env.get(proto.K_SRC)
    room = env.get(proto.K_ROOM)
    body = env.get(proto.K_BODY)
    row["t"] = env.get(proto.K_T)
    row["mid"] = bytes(mid).hex() if isinstance(mid, (bytes, bytearray)) else None
    row["src"] = bytes(src).hex() if isinstance(src, (bytes, bytearray)) else None
    row["room"] = room if isinstance(room, str) else None
    if isinstance(body, str):
        row["body"] = body[:120]
        row["is_command"] = body.strip().startswith("/")
    return row


def write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    os.replace(tmp, path)


def sample_interface_stats(rns, traffic):
    try:
        stats = rns.get_interface_stats()
    except Exception:
        return
    rows = stats.get("interfaces", []) if isinstance(stats, dict) else []
    interfaces = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        interfaces.append(
            {
                "name": row.get("name"),
                "status": bool(row.get("status")),
                "rxb": row.get("rxb"),
                "txb": row.get("txb"),
                "rxs": row.get("rxs"),
                "txs": row.get("txs"),
            },
        )
    traffic.write({"ts": time.time(), "ev": "ifstats", "interfaces": interfaces})


def install_hub_logging(server, traffic):
    orig_on_packet = server._on_packet

    def on_packet(link, data):
        row = {"ts": time.time(), "ev": "in", "peer": server._peer_label_for(link)}
        row.update(envelope_fields(data))
        traffic.write(row)
        return orig_on_packet(link, data)

    server._on_packet = on_packet

    orig_send_payload = server._send_payload

    def send_payload(link, payload):
        row = {"ts": time.time(), "ev": "out", "peer": server._peer_label_for(link)}
        row.update(envelope_fields(payload))
        traffic.write(row)
        return orig_send_payload(link, payload)

    server._send_payload = send_payload

    orig_on_link = server._on_link

    def on_link(link):
        traffic.write({"ts": time.time(), "ev": "link_open"})
        return orig_on_link(link)

    server._on_link = on_link

    orig_on_close = server._on_close

    def on_close(link):
        traffic.write({"ts": time.time(), "ev": "link_close"})
        return orig_on_close(link)

    server._on_close = on_close

    if server.destination is not None:
        server.destination.set_link_established_callback(server._on_link)


def install_drop_route(server):
    """Accept chat envelopes without relaying, for held-delivery tests."""
    orig_route = server._route

    def route(link, sess, env, outgoing):
        if env.get(proto.K_T) in (proto.T_MSG, proto.T_ACTION):
            return None
        return orig_route(link, sess, env, outgoing)

    server._route = route


def run_hub(config_dir, share_dir, port, announce_interval, rate_limit, drop_msgs):
    rns = RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    traffic = TrafficLog(os.path.join(share_dir, "hub_traffic.jsonl"))

    storage = os.path.join(config_dir, "rrc_server")
    manager = RRCServerManager(storage)
    manager.load()
    if manager.hubs:
        server = manager.hubs[0]
        if not server.running:
            server.start()
    else:
        server = manager.create_hub(
            name="Live rrcd",
            greeting="live harness hub",
            announce=True,
            announce_interval_seconds=announce_interval,
            rate_limit_msgs_per_minute=rate_limit,
            enabled=True,
        )
        server.register_room("lobby", topic="the lobby")

    install_hub_logging(server, traffic)
    if drop_msgs:
        install_drop_route(server)

    write_json(
        os.path.join(share_dir, "hub_ready.json"),
        {
            "dest": server.dest_hash.hex(),
            "pub": server.identity.get_public_key().hex(),
            "rate_limit": server.rate_limit_msgs_per_minute,
            "port": port,
        },
    )

    stop_path = os.path.join(share_dir, "hub_stop")
    announce_path = os.path.join(share_dir, "hub_announce")
    while not os.path.isfile(stop_path):
        if os.path.isfile(announce_path):
            with contextlib.suppress(Exception):
                os.unlink(announce_path)
            with contextlib.suppress(Exception):
                server.announce_now()
            traffic.write({"ts": time.time(), "ev": "announce_sent"})
        sample_interface_stats(rns, traffic)
        traffic.write(
            {
                "ts": time.time(),
                "ev": "hub_stats",
                "stats": dict(server._stats),
                "sessions": len(server._sessions),
            },
        )
        deadline = time.monotonic() + STATS_INTERVAL_S
        while time.monotonic() < deadline:
            if os.path.isfile(stop_path):
                break
            time.sleep(STOP_POLL_S)

    traffic.write({"ts": time.time(), "ev": "stopping"})
    manager.shutdown()
    RNS.exit(0)


def run_zombie(config_dir, share_dir, port, announce_interval):
    """Announce an rrc.hub destination that never completes a link."""
    rns = RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    traffic = TrafficLog(os.path.join(share_dir, "hub_traffic.jsonl"))

    identity_path = os.path.join(config_dir, "zombie_identity")
    identity = None
    if os.path.isfile(identity_path):
        identity = RNS.Identity.from_file(identity_path)
    if identity is None:
        identity = RNS.Identity()
        identity.to_file(identity_path)

    app_name, aspects = RNS.Destination.app_and_aspects_from_name(
        proto.DEFAULT_DEST_NAME,
    )
    destination = RNS.Destination(
        identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        app_name,
        *aspects,
    )
    destination.set_proof_strategy(RNS.Destination.PROVE_NONE)

    write_json(
        os.path.join(share_dir, "hub_ready.json"),
        {
            "dest": destination.hash.hex(),
            "pub": identity.get_public_key().hex(),
            "port": port,
        },
    )

    stop_path = os.path.join(share_dir, "hub_stop")
    interval = max(1.0, float(announce_interval))
    while not os.path.isfile(stop_path):
        try:
            destination.announce(
                app_data=proto.encode({"proto": "rrc", "v": 1, "hub": "zombie"}),
            )
            traffic.write({"ts": time.time(), "ev": "announce_sent"})
        except Exception as exc:
            traffic.write(
                {"ts": time.time(), "ev": "announce_failed", "error": str(exc)}
            )
        sample_interface_stats(rns, traffic)
        deadline = time.monotonic() + interval
        while time.monotonic() < deadline:
            if os.path.isfile(stop_path):
                break
            time.sleep(STOP_POLL_S)

    traffic.write({"ts": time.time(), "ev": "stopping"})
    RNS.exit(0)


def main():
    config_dir = sys.argv[1]
    share_dir = sys.argv[2]
    port = int(sys.argv[3])
    announce_interval = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    rate_limit = int(sys.argv[5]) if len(sys.argv) > 5 else 120
    mode = sys.argv[6] if len(sys.argv) > 6 else "hub"
    drop_msgs = len(sys.argv) > 7 and sys.argv[7] == "1"

    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(share_dir, exist_ok=True)

    if mode == "zombie":
        run_zombie(config_dir, share_dir, port, announce_interval)
        return
    run_hub(config_dir, share_dir, port, announce_interval, rate_limit, drop_msgs)


if __name__ == "__main__":
    main()
