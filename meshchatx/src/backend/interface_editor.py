# SPDX-License-Identifier: 0BSD AND MIT

import re

_IPV4_HOST_PORT = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")


def normalize_rnode_tcp_port(port: str) -> str:
    """Normalize RNodeInterface ``port`` when using ``tcp://``.

    Reticulum's ``TCPConnection`` (``RNS/Interfaces/RNodeInterface.py``) calls
    ``socket.getaddrinfo(target_host, 7633)``. The first argument must be a hostname or IP **only**; an embedded ``:port``
    breaks resolution. Config may list legacy ``tcp://host:7633`` or ``tcp://host:``;
    strip those so storage matches ``tcp://<host>``.
    """
    raw = str(port).strip()
    low = raw.lower()
    scheme = "tcp://"
    if not low.startswith(scheme):
        return raw
    rest = raw[len(scheme) :].strip()
    while rest.endswith(":"):
        rest = rest[:-1]
    if not rest:
        return scheme
    if rest.startswith("["):
        close = rest.find("]")
        if close != -1 and len(rest) > close + 1 and rest[close + 1] == ":":
            tail = rest[close + 2 :]
            if tail.isdigit() and 1 <= int(tail) <= 65535:
                rest = rest[: close + 1]
        return scheme + rest
    m = _IPV4_HOST_PORT.match(rest)
    if m and int(m.group(2)) <= 65535:
        rest = m.group(1)
    elif rest.count(":") == 1:
        head, tail = rest.split(":", 1)
        if tail.isdigit() and 1 <= int(tail) <= 65535:
            rest = head
    return scheme + rest


def coerce_rnode_frequency_hz(value):
    """Return RNode carrier frequency as integer Hz for Reticulum config.

    Reticulum reads ``frequency`` with ``int()``; MHz-style decimals (868.825)
    must not be stored verbatim or they truncate to invalid values. Accepts
    Hz integers, bare MHz-style numbers below 1e6, and strings with optional
    ghz/mhz/khz/hz suffix (ASCII, case-insensitive).
    """
    if value is None or value == "":
        return value
    raw = str(value).strip()
    s = raw.lower().replace("_", "")
    mult = 1.0
    for suffix, m in (("ghz", 1e9), ("mhz", 1e6), ("khz", 1e3), ("hz", 1.0)):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            mult = m
            break
    f = float(s) * mult
    if f <= 0:
        return int(round(f))
    if f >= 1_000_000:
        return int(round(f))
    is_integer = abs(f - round(f)) < 1e-9
    if (not is_integer) or (is_integer and f < 10_000):
        f *= 1_000_000.0
    return int(round(f))


class InterfaceEditor:
    coerce_rnode_frequency_hz = staticmethod(coerce_rnode_frequency_hz)
    normalize_rnode_tcp_port = staticmethod(normalize_rnode_tcp_port)

    @staticmethod
    def update_value(interface_details: dict, data: dict, key: str):
        # update value if provided and not empty
        value = data.get(key)
        if value is not None and value != "":
            interface_details[key] = value
            return

        # otherwise remove existing value
        interface_details.pop(key, None)
