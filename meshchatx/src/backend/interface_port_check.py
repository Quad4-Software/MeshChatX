# SPDX-License-Identifier: 0BSD AND MIT

"""Helpers for validating that user supplied interface ports are usable.

These helpers attempt to bind to the requested port on the requested host so
that the UI can warn the operator before saving a configuration that would
fail to come up after restart. The checks are intentionally best-effort: they
only catch ports that are *currently* in use by another process, they do not
guarantee that the port will still be free at restart time.
"""

from __future__ import annotations

import contextlib
import errno
import socket


_PORT_IN_USE_ERRNOS = {
    errno.EADDRINUSE,
    errno.EACCES,
    errno.EADDRNOTAVAIL,
}


def _normalize_host(host: str | None) -> str:
    """Return a host string that is safe to call ``getaddrinfo`` with."""
    if host is None:
        return ""
    host = str(host).strip()
    if host == "" or host in {"*", "0.0.0.0", "::", "[::]"}:
        return ""
    return host


def _coerce_port(port) -> int | None:
    if port is None or port == "":
        return None
    try:
        value = int(port)
    except (TypeError, ValueError):
        return None
    if value < 0 or value > 65535:
        return None
    return value


def is_port_in_use(host: str | None, port, *, kind: str = "tcp") -> bool:
    """Return ``True`` when the given ``host``:``port`` is already bound.

    ``kind`` may be ``"tcp"`` or ``"udp"``. Unknown values are treated as TCP.

    The helper resolves the supplied host (falling back to ``INADDR_ANY``) and
    tries to bind a fresh socket. ``EADDRINUSE``/``EACCES``/``EADDRNOTAVAIL``
    are reported as "in use", any other exception bubbles up as ``False`` so
    that we never block save flows because of a transient resolution glitch.
    """
    coerced_port = _coerce_port(port)
    if coerced_port is None or coerced_port == 0:
        return False

    sock_kind = socket.SOCK_DGRAM if str(kind).lower() == "udp" else socket.SOCK_STREAM

    normalized = _normalize_host(host)
    candidates: list[tuple[int, str]] = []
    if normalized == "":
        candidates.append((socket.AF_INET, "0.0.0.0"))
        candidates.append((socket.AF_INET6, "::"))
    else:
        try:
            infos = socket.getaddrinfo(
                normalized,
                coerced_port,
                type=sock_kind,
            )
        except OSError:
            return False
        seen: set[tuple[int, str]] = set()
        for info in infos:
            family = info[0]
            if family not in (socket.AF_INET, socket.AF_INET6):
                continue
            address = info[4][0]
            key = (family, address)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(key)

    for family, address in candidates:
        with contextlib.closing(socket.socket(family, sock_kind)) as sock:
            try:
                if sock_kind == socket.SOCK_STREAM:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((address, coerced_port))
            except OSError as exc:
                if exc.errno in _PORT_IN_USE_ERRNOS:
                    return True
                continue

    return False


def describe_port_conflict(
    host: str | None,
    port,
    *,
    kind: str = "tcp",
    interface_name: str | None = None,
) -> str:
    """Build a user-facing message describing a port conflict."""
    coerced_port = _coerce_port(port)
    host_label = _normalize_host(host) or "0.0.0.0"
    name_part = f' for interface "{interface_name}"' if interface_name else ""
    proto = str(kind).upper()
    if coerced_port is None:
        return (
            f"The configured {proto} port{name_part} is invalid. "
            "Please pick a value between 1 and 65535."
        )
    return (
        f"The {proto} port {coerced_port} on {host_label} is already in "
        f"use by another process{name_part}. Stop the conflicting process "
        "or pick a different port."
    )
