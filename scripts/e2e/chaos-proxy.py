#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Minimal TCP chaos proxy for e2e fault injection.

Sits between the live peer and the backend TCPServerInterface. Forwards
bytes bidirectionally by default. A control file is polled and switches
the fault mode without restarting the proxy:

    pass          - transparent forwarding
    drop          - close all connections, keep accepting (new conns pass)
    partition     - blackhole all traffic, keep connections open
    latency:MS    - delay each chunk by MS milliseconds
    rate:BPS      - cap throughput at BPS bytes per second
    error         - close the listening socket to inbound connects

Usage: chaos-proxy.py LISTEN_PORT TARGET_PORT CONTROL_FILE
"""

import asyncio
import os
import sys

MODE = {"name": "pass", "arg": 0}
CONNS = set()


def read_mode(path):
    try:
        with open(path) as f:
            raw = f.read().strip()
    except OSError:
        return
    if not raw:
        return
    if ":" in raw:
        name, arg = raw.split(":", 1)
        try:
            MODE["name"], MODE["arg"] = name, float(arg)
            return
        except ValueError:
            pass
    MODE["name"], MODE["arg"] = raw, 0


async def pump(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            mode, arg = MODE["name"], MODE["arg"]
            if mode == "partition":
                await asyncio.sleep(0.1)
                continue
            if mode == "latency" and arg > 0:
                await asyncio.sleep(arg / 1000.0)
            elif mode == "rate" and arg > 0:
                await asyncio.sleep(len(data) / arg)
            writer.write(data)
            await writer.drain()
    except (OSError, asyncio.CancelledError):
        pass
    finally:
        with __import__("contextlib").suppress(Exception):
            writer.close()


async def handle(reader, writer, target_port):
    if MODE["name"] == "error":
        writer.close()
        return
    try:
        t_reader, t_writer = await asyncio.open_connection(
            "127.0.0.1", target_port
        )
    except OSError:
        writer.close()
        return
    CONNS.add(writer)
    CONNS.add(t_writer)
    try:
        await asyncio.gather(
            pump(reader, t_writer), pump(t_reader, writer)
        )
    finally:
        CONNS.discard(writer)
        CONNS.discard(t_writer)


async def main():
    listen_port, target_port, control = (
        int(sys.argv[1]),
        int(sys.argv[2]),
        sys.argv[3],
    )
    server = await asyncio.start_server(
        lambda r, w: handle(r, w, target_port), "127.0.0.1", listen_port
    )

    async def control_loop():
        prev = None
        while True:
            read_mode(control)
            mode = MODE["name"]
            if mode != prev:
                print(f"[chaos] mode -> {mode}:{MODE['arg']}", flush=True)
                if mode == "drop":
                    for w in list(CONNS):
                        try:
                            w.close()
                        except OSError:
                            pass
                prev = mode
            await asyncio.sleep(0.1)

    async with server:
        await control_loop()


if __name__ == "__main__":
    if os.environ.get("CHAOS_PROXY_NO_RUN"):
        sys.exit(0)
    asyncio.run(main())
