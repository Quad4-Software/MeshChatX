#!/usr/bin/env python3
"""Subprocess helper for live Reticulum HTTP tunnel tests."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj) + "\n", encoding="utf-8")


def cmd_serve(args):
    import RNS

    RNS.Reticulum(
        configdir=args.configdir,
        loglevel=RNS.LOG_NOTICE,
    )
    identity = RNS.Identity()
    destination = RNS.Destination(
        identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        "http_live",
        "echo",
    )

    received = {"payload": None}

    def packet_callback(data, packet):
        try:
            text = data.decode("utf-8")
        except Exception:
            text = None
        received["payload"] = text
        write_json(Path(args.recv_file), {"payload": text})

    destination.set_packet_callback(packet_callback)
    destination.announce()
    Path(args.announce_file).write_text(destination.hash.hex() + "\n", encoding="utf-8")

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if received["payload"] is not None:
            time.sleep(1.0)
            return 0
        time.sleep(0.1)

    write_json(Path(args.recv_file), {"payload": None, "error": "timeout"})
    return 1


def cmd_client(args):
    import RNS

    reticulum = RNS.Reticulum(
        configdir=args.configdir,
        loglevel=RNS.LOG_NOTICE,
    )
    RNS.Identity()
    target_hash = bytes.fromhex(args.target_hash)

    if not RNS.Transport.has_path(target_hash):
        RNS.Transport.request_path(target_hash)

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if RNS.Transport.has_path(target_hash):
            break
        RNS.Transport.request_path(target_hash)
        time.sleep(0.25)
    else:
        write_json(
            Path(args.done_file),
            {"ok": False, "error": "path_timeout"},
        )
        return 1

    recalled = RNS.Identity.recall(target_hash)
    if recalled is None:
        write_json(
            Path(args.done_file),
            {"ok": False, "error": "identity_recall_failed"},
        )
        return 1

    dest = RNS.Destination(
        recalled,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "http_live",
        "echo",
    )
    packet = RNS.Packet(dest, args.payload.encode("utf-8"))
    packet.send()

    write_json(
        Path(args.done_file),
        {
            "ok": True,
            "path": True,
            "shared": reticulum.is_shared_instance,
        },
    )
    time.sleep(3.0)
    return 0


def cmd_local_client(args):
    import RNS

    reticulum = RNS.Reticulum(
        configdir=args.configdir,
        loglevel=RNS.LOG_NOTICE,
        require_shared_instance=True,
    )

    connected = reticulum.is_connected_to_shared_instance
    expect = bytes.fromhex(args.expect_hash)

    deadline = time.monotonic() + min(args.timeout, 20.0)
    has_path = False
    while time.monotonic() < deadline:
        if RNS.Transport.has_path(expect):
            has_path = True
            break
        RNS.Transport.request_path(expect)
        time.sleep(0.3)

    ok = bool(connected)
    write_json(
        Path(args.done_file),
        {
            "ok": ok,
            "connected_to_shared": connected,
            "has_path": has_path,
            "is_shared_instance": reticulum.is_shared_instance,
        },
    )
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--configdir", required=True)
    p_serve.add_argument("--announce-file", required=True)
    p_serve.add_argument("--recv-file", required=True)
    p_serve.add_argument("--timeout", type=float, default=120.0)
    p_serve.set_defaults(func=cmd_serve)

    p_client = sub.add_parser("client")
    p_client.add_argument("--configdir", required=True)
    p_client.add_argument("--target-hash", required=True)
    p_client.add_argument("--done-file", required=True)
    p_client.add_argument("--payload", required=True)
    p_client.add_argument("--timeout", type=float, default=90.0)
    p_client.set_defaults(func=cmd_client)

    p_local = sub.add_parser("local_client")
    p_local.add_argument("--configdir", required=True)
    p_local.add_argument("--done-file", required=True)
    p_local.add_argument("--expect-hash", required=True)
    p_local.add_argument("--timeout", type=float, default=45.0)
    p_local.set_defaults(func=cmd_local_client)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"peer error: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
