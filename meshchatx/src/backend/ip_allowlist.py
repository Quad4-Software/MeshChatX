# SPDX-License-Identifier: 0BSD

"""IP/CIDR allowlist for web UI access."""

from __future__ import annotations

import ipaddress
import re


def normalize_allowlist_text(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_allowlist_entries(text: str | None) -> list[str]:
    raw = normalize_allowlist_text(text)
    if not raw:
        return []
    parts = re.split(r"[\s,;]+", raw)
    return [p.strip() for p in parts if p.strip()]


def parse_allowlist_networks(text: str | None) -> list[ipaddress._BaseNetwork]:
    entries = parse_allowlist_entries(text)
    networks: list[ipaddress._BaseNetwork] = []
    for entry in entries:
        try:
            if "/" in entry:
                networks.append(ipaddress.ip_network(entry, strict=False))
            else:
                addr = ipaddress.ip_address(entry)
                width = addr.max_prefixlen
                networks.append(ipaddress.ip_network(f"{addr}/{width}", strict=False))
        except ValueError as exc:
            msg = f"Invalid allowlist entry: {entry!r}"
            raise ValueError(msg) from exc
    return networks


def client_ip_allowed(client_ip: str, allowlist_text: str | None) -> bool:
    entries = parse_allowlist_entries(allowlist_text)
    if not entries:
        return True
    if not client_ip:
        return False
    try:
        addr = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        return False
    for network in parse_allowlist_networks(allowlist_text):
        if addr in network:
            return True
    return False
