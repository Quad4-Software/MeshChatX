# SPDX-License-Identifier: 0BSD

"""Host network interface enumeration for the interfaces API."""

from __future__ import annotations

import logging
import socket

import psutil


def list_host_network_interfaces():
    """Enumerate kernel network interfaces on the host running MeshChat.

    Uses psutil (Linux, macOS, Windows). Fails soft on restricted environments
    (e.g. some Android sandboxes) and returns ([], error).

    Reticulum's device field on server-style interfaces is a *single* interface
    name, or omitted when binding only via listen_ip.
    """
    try:
        raw = psutil.net_if_addrs()
    except Exception as exc:
        logging.debug("list_host_network_interfaces: net_if_addrs failed: %s", exc)
        return [], str(exc)
    out: list[dict[str, object]] = []
    for name in sorted(raw.keys(), key=lambda n: str(n).lower()):
        addrs: list[str] = []
        for addr in raw[name]:
            if addr.family == socket.AF_INET:
                addrs.append(addr.address)
            elif addr.family == socket.AF_INET6:
                if addr.address.startswith("fe80:"):
                    continue
                addrs.append(addr.address)
        out.append({"name": name, "addresses": addrs})
    return out, None
