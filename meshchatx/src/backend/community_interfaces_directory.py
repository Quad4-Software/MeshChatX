# SPDX-License-Identifier: 0BSD

"""Convert directory.rns.recipes listing rows into MeshChat interface preset dicts."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

DEFAULT_SUBMITTED_URL = (
    "https://directory.rns.recipes/api/directory/submitted?search=&type=&status=online"
)

DESCRIPTION = "directory.rns.recipes (user-submitted, online)"

_ALLOWED_DIRECTORY_HOSTS = frozenset({"directory.rns.recipes"})


def validate_directory_fetch_url(url: str) -> str:
    """Reject SSRF: only https to directory.rns.recipes, no credentials."""
    if not url or not isinstance(url, str):
        msg = "URL must be a non-empty string"
        raise ValueError(msg)
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        msg = "Community directory URL must use https"
        raise ValueError(msg)
    netloc = parsed.netloc or ""
    if "@" in netloc:
        msg = "Community directory URL must not contain credentials"
        raise ValueError(msg)
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_DIRECTORY_HOSTS:
        msg = "Community directory URL host is not allowed"
        raise ValueError(msg)
    return url.strip()


class _DirectoryFetchNoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """urllib follows redirects by default; blocked to prevent SSRF via Location."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            "Redirects are not followed for community directory fetch",
            headers,
            fp,
        )


_DIRECTORY_FETCH_OPENER = urllib.request.build_opener(_DirectoryFetchNoRedirectHandler())


def fetch_directory_payload(url: str, *, timeout: float = 60.0) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MeshChatX-community-interfaces/1.0 (+https://meshchatx.com/)",
        },
        method="GET",
    )
    with _DIRECTORY_FETCH_OPENER.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_interfaces_from_directory_url(
    url: str | None = None,
    *,
    timeout: float = 60.0,
) -> tuple[list[dict[str, Any]], str]:
    if url is not None and str(url).strip():
        resolved = validate_directory_fetch_url(url)
    else:
        resolved = DEFAULT_SUBMITTED_URL
    payload = fetch_directory_payload(resolved, timeout=timeout)
    rows = rows_from_payload(payload)
    return transform_directory_rows(rows), resolved


_RE_REMOTE = re.compile(r"^\s*remote\s*=\s*(\S+)", re.MULTILINE | re.IGNORECASE)
_RE_TARGET_HOST = re.compile(
    r"^\s*target_host\s*=\s*(\S+)",
    re.MULTILINE | re.IGNORECASE,
)
_RE_TRANSPORT_IDENTITY = re.compile(
    r"^\s*transport_identity\s*=\s*(\S+)",
    re.MULTILINE | re.IGNORECASE,
)
_RE_PEERS_LINE = re.compile(r"^\s*peers\s*=\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def rows_from_payload(payload: object) -> list[Any]:
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, list):
            return data
    if isinstance(payload, list):
        return payload
    raise ValueError("Expected list or object with 'data' array")


def _parse_config_value(pattern: re.Pattern[str], cfg: str) -> str:
    m = pattern.search(cfg)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def _first_peer_from_config(cfg: str) -> str:
    raw = _parse_config_value(_RE_PEERS_LINE, cfg)
    if not raw:
        return ""
    for part in raw.replace(",", " ").split():
        p = part.strip().strip('"').strip("'")
        if p:
            return p
    return ""


def _tcp_host_from_row(row: dict[str, Any], cfg: str) -> str:
    h = (row.get("host") or row.get("address") or "").strip()
    if h:
        return h
    return _parse_config_value(_RE_REMOTE, cfg) or _parse_config_value(
        _RE_TARGET_HOST,
        cfg,
    )


def _i2p_peer(row: dict[str, Any], cfg: str) -> str:
    h = (row.get("host") or row.get("address") or "").strip()
    if h:
        return h
    return _first_peer_from_config(cfg)


def _transport_id(row: dict[str, Any], cfg: str) -> str:
    tid = row.get("transportId")
    if tid is not None and str(tid).strip():
        return str(tid).strip()
    return _parse_config_value(_RE_TRANSPORT_IDENTITY, cfg)


def transform_directory_rows(rows: list[Any]) -> list[dict[str, Any]]:
    out_list: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out_list

    for row in rows:
        if not isinstance(row, dict):
            continue

        name = (row.get("name") or "").strip()
        rtype = (row.get("type") or "").lower()
        type_name = row.get("typeName") or ""
        if not isinstance(type_name, str):
            type_name = str(type_name)
        cfg = row.get("config") or ""
        if not isinstance(cfg, str):
            cfg = ""

        if rtype == "rnode":
            continue

        if rtype == "i2p":
            addr = _i2p_peer(row, cfg)
            if not addr:
                continue
            out_list.append(
                {
                    "name": name or addr,
                    "type": "I2PInterface",
                    "i2p_peers": [addr],
                    "description": DESCRIPTION,
                },
            )
            continue

        port = row.get("port")
        if port is None or port == "":
            continue
        try:
            port_i = int(port)
        except (TypeError, ValueError):
            continue

        addr = _tcp_host_from_row(row, cfg)
        if not addr:
            continue

        tid = _transport_id(row, cfg)
        backbone_in_type = rtype == "backbone" or type_name == "BackboneInterface"
        backbone_in_tcp = rtype == "tcp" and "BackboneInterface" in cfg
        is_backboneish = backbone_in_type or backbone_in_tcp
        is_tcp_style = rtype == "tcp" or type_name == "TCPClientInterface"

        if is_backboneish and tid:
            out_list.append(
                {
                    "name": name,
                    "type": "BackboneInterface",
                    "remote": addr,
                    "target_port": port_i,
                    "transport_identity": tid,
                    "description": DESCRIPTION,
                },
            )
            continue

        if is_backboneish and not tid:
            out_list.append(
                {
                    "name": name,
                    "type": "TCPClientInterface",
                    "target_host": addr,
                    "target_port": port_i,
                    "description": DESCRIPTION,
                },
            )
            continue

        if is_tcp_style:
            out_list.append(
                {
                    "name": name,
                    "type": "TCPClientInterface",
                    "target_host": addr,
                    "target_port": port_i,
                    "description": DESCRIPTION,
                },
            )

    return out_list
