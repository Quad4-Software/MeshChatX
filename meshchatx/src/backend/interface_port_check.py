# SPDX-License-Identifier: 0BSD

"""Best-effort checks that a configured listen port can be bound right now."""

from __future__ import annotations

import contextlib
import errno
import socket

_BUSY_ERRNOS = frozenset(
    {
        errno.EADDRINUSE,
        errno.EACCES,
        errno.EADDRNOTAVAIL,
    },
)


def _host_for_bind(host: str | None) -> str:
    if host is None:
        return ""
    text = str(host).strip()
    if text in {"", "*", "0.0.0.0", "::", "[::]"}:
        return ""
    return text


def _port_int(port: object) -> int | None:
    if port is None or port == "":
        return None
    try:
        value = int(port)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if value < 0 or value > 65535:
        return None
    return value


def is_port_in_use(host: str | None, port: object, *, kind: str = "tcp") -> bool:
    """Return True when host:port appears already bound.

    kind is tcp or udp. Failures other than busy-bind errnos return False so
    the UI never blocks a save on transient DNS or permission noise.
    """
    port_num = _port_int(port)
    if port_num is None or port_num == 0:
        return False

    sock_type = socket.SOCK_DGRAM if str(kind).lower() == "udp" else socket.SOCK_STREAM
    host_text = _host_for_bind(host)
    targets: list[tuple[socket.AddressFamily, str]] = []

    if host_text == "":
        targets.append((socket.AF_INET, "0.0.0.0"))
        targets.append((socket.AF_INET6, "::"))
    else:
        try:
            infos = socket.getaddrinfo(host_text, port_num, type=sock_type)
        except OSError:
            return False
        seen: set[tuple[socket.AddressFamily, str]] = set()
        for info in infos:
            family = info[0]
            if family not in (socket.AF_INET, socket.AF_INET6):
                continue
            address = str(info[4][0])
            key = (family, address)
            if key in seen:
                continue
            seen.add(key)
            targets.append(key)

    for family, address in targets:
        with contextlib.closing(socket.socket(family, sock_type)) as sock:
            try:
                if sock_type == socket.SOCK_STREAM:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((address, port_num))
            except OSError as exc:
                if exc.errno in _BUSY_ERRNOS:
                    return True
                continue

    return False


def describe_port_conflict(
    host: str | None,
    port: object,
    *,
    kind: str = "tcp",
    interface_name: str | None = None,
) -> str:
    """User-facing explanation of a bad or busy port setting."""
    port_num = _port_int(port)
    host_label = _host_for_bind(host) or "0.0.0.0"
    name_bit = f' for interface "{interface_name}"' if interface_name else ""
    proto = str(kind).upper()
    if port_num is None:
        return (
            f"The configured {proto} port{name_bit} is invalid. "
            "Please pick a value between 1 and 65535."
        )
    return (
        f"The {proto} port {port_num} on {host_label} is already in "
        f"use by another process{name_bit}. Stop the conflicting process "
        "or pick a different port."
    )
