# SPDX-License-Identifier: 0BSD

"""Scripted RRC client process for the rrcd interoperability tests.

Runs a real RRCManager against a real Reticulum instance with a TCP
client interface, driven by JSON commands appended to commands.jsonl.
Every outbound and inbound envelope, path request, announce, and status
transition is appended to client_traffic.jsonl so tests can assert on
real wire behaviour.

Usage:
    python rrc_client.py <config_dir> <share_dir> <hubs_json>

Commands:
    {"op": "connect"}
    {"op": "join", "room": "lobby"}
    {"op": "send", "room": "lobby", "text": "hello"}
    {"op": "retry", "room": "lobby", "seq": 3}
    {"op": "sweep", "room": "lobby"}
    {"op": "snapshot"}
    {"op": "exit"}
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

from meshchatx.src.backend.announce_handler import AnnounceHandler
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager

COMMAND_POLL_S = 0.1


class EventLog:
    """Append-only JSONL writer shared across RNS callback threads."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def write(self, row):
        row.setdefault("ts", time.time())
        with self._lock:
            try:
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, default=str) + "\n")
            except Exception:
                pass


def envelope_fields(data):
    row = {"bytes": len(data)}
    try:
        env = proto.decode(data)
    except Exception:
        return row
    if not isinstance(env, dict):
        return row
    mid = env.get(proto.K_ID)
    room = env.get(proto.K_ROOM)
    body = env.get(proto.K_BODY)
    row["t"] = env.get(proto.K_T)
    row["mid"] = bytes(mid).hex() if isinstance(mid, (bytes, bytearray)) else None
    row["room"] = room if isinstance(room, str) else None
    if isinstance(body, str):
        row["body"] = body[:120]
        row["is_command"] = body.strip().startswith("/")
    return row


def load_or_create_identity(config_dir):
    path = os.path.join(config_dir, "client_identity")
    identity = None
    if os.path.isfile(path):
        identity = RNS.Identity.from_file(path)
    if identity is None:
        identity = RNS.Identity()
        identity.to_file(path)
    return identity


def install_traffic_hooks(log):
    orig_raw_send = RRCHub._raw_send

    def raw_send(self, link, payload):
        row = {"ev": "out", "hub": self.hub_hash.hex()}
        row.update(envelope_fields(payload))
        log.write(row)
        return orig_raw_send(self, link, payload)

    RRCHub._raw_send = raw_send

    orig_send_env = RRCHub._send_env

    def send_env(self, env):
        payload = proto.encode(env)
        row = {"ev": "out", "hub": self.hub_hash.hex()}
        row.update(envelope_fields(payload))
        log.write(row)
        return orig_send_env(self, env)

    RRCHub._send_env = send_env

    orig_on_packet = RRCHub._on_packet

    def on_packet(self, data):
        row = {"ev": "in", "hub": self.hub_hash.hex()}
        row.update(envelope_fields(data))
        log.write(row)
        return orig_on_packet(self, data)

    RRCHub._on_packet = on_packet

    orig_request_path = RNS.Transport.request_path

    def request_path(destination_hash, *args, **kwargs):
        try:
            dest = bytes(destination_hash).hex()
        except Exception:
            dest = None
        log.write({"ev": "path_request", "dest": dest})
        return orig_request_path(destination_hash, *args, **kwargs)

    RNS.Transport.request_path = staticmethod(request_path)


def snapshot_state(manager):
    hubs = []
    for hub in manager.hubs:
        messages = {}
        with hub._lock:
            rooms = sorted(hub.rooms)
            for room in rooms:
                messages[room] = [
                    {
                        "seq": m.seq,
                        "kind": m.kind,
                        "text": m.text,
                        "delivery": getattr(m, "delivery", None),
                        "dup_count": getattr(m, "dup_count", 1),
                        "mid": bytes(m.mid).hex()
                        if isinstance(getattr(m, "mid", None), (bytes, bytearray))
                        else None,
                    }
                    for m in hub.messages.get(room, [])
                ]
        hubs.append(
            {
                "hash": hub.hub_hash.hex(),
                "status": hub.status,
                "welcomed": bool(hub.welcomed),
                "reconnect_attempts": hub._reconnect_attempts,
                "rooms": rooms,
                "messages": messages,
            },
        )
    return {"ev": "state", "hubs": hubs}


def handle_command(manager, log, command):
    op = command.get("op")
    result = {"ev": "op", "op": op, "ok": True}
    try:
        if op == "connect":
            manager.connect_auto_reconnect_hubs()
        elif op == "join":
            room = command.get("room", "lobby")
            for hub in manager.hubs:
                with hub._lock:
                    connected = hub.status == RRCHub.STATUS_CONNECTED
                if connected and room not in hub.rooms:
                    hub.join_room(room)
        elif op == "send":
            room = command.get("room", "lobby")
            text = command.get("text", "")
            hub = manager.hubs[0]
            mid = hub.send_message(room, text)
            result["mid"] = mid.hex() if isinstance(mid, (bytes, bytearray)) else None
        elif op == "retry":
            room = command.get("room", "lobby")
            seq = int(command.get("seq", 0))
            hub = manager.hubs[0]
            mid = hub.retry_message(room, seq)
            result["mid"] = mid.hex() if isinstance(mid, (bytes, bytearray)) else None
        elif op == "sweep":
            room = command.get("room", "lobby")
            manager.hubs[0].room_messages(room)
        elif op == "snapshot":
            for hub in manager.hubs:
                with hub._lock:
                    rooms = list(hub.rooms)
                for room in rooms:
                    with contextlib.suppress(Exception):
                        hub.room_messages(room)
            log.write(snapshot_state(manager))
        elif op == "exit":
            result["exit"] = True
        else:
            result["ok"] = False
            result["error"] = "unknown op"
    except Exception as exc:
        result["ok"] = False
        result["error"] = type(exc).__name__ + ": " + str(exc)
    log.write(result)
    return bool(result.get("exit"))


def main():
    config_dir = sys.argv[1]
    share_dir = sys.argv[2]
    hubs_path = sys.argv[3]

    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(share_dir, exist_ok=True)

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    log = EventLog(os.path.join(share_dir, "client_traffic.jsonl"))

    identity = load_or_create_identity(config_dir)
    manager = RRCManager(identity=identity, storage_dir=os.path.join(config_dir, "rrc"))
    manager.load()

    with open(hubs_path, encoding="utf-8") as handle:
        hub_hashes = json.load(handle)
    for hub_hex in hub_hashes:
        manager.add_hub(bytes.fromhex(hub_hex))

    def on_change(hub=None):
        if hub is None:
            return
        log.write(
            {
                "ev": "status",
                "hub": hub.hub_hash.hex(),
                "status": hub.status,
                "welcomed": bool(hub.welcomed),
                "reconnect_attempts": hub._reconnect_attempts,
            },
        )

    manager.set_change_callback(on_change)
    install_traffic_hooks(log)

    def on_announce(
        aspect, destination_hash, announced_identity, app_data, packet_hash
    ):
        hub = manager.find_hub_by_hex(destination_hash.hex())
        log.write(
            {"ev": "announce", "hub": destination_hash.hex(), "known": hub is not None}
        )
        if hub is not None:
            hub.note_hub_announce()

    RNS.Transport.register_announce_handler(AnnounceHandler("rrc.hub", on_announce))

    commands_path = os.path.join(share_dir, "commands.jsonl")
    offset = 0
    log.write({"ev": "ready"})
    while True:
        if os.path.isfile(commands_path):
            with open(commands_path, encoding="utf-8") as handle:
                handle.seek(offset)
                while True:
                    line = handle.readline()
                    if not line:
                        break
                    offset = handle.tell()
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        command = json.loads(line)
                    except Exception:
                        continue
                    if handle_command(manager, log, command):
                        log.write({"ev": "exiting"})
                        RNS.exit(0)
                        return
        time.sleep(COMMAND_POLL_S)


if __name__ == "__main__":
    main()
