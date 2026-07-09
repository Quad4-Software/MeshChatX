# SPDX-License-Identifier: 0BSD

"""Helpers for WebSocket JSON message contract checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

_CLIENT_HANDLER_RE = re.compile(
    r"(?:if|elif)\s+_type\s*==\s*[\"']([^\"']+)[\"']",
)
_WS_SEND_STR_RE = re.compile(
    r"client\.send_str\s*\(\s*json\.dumps\s*\(\s*(\{[\s\S]*?\})\s*,?\s*\)",
)
_RNS_LINK_SEND_RE = re.compile(
    r"_rns_link_send\s*\(\s*client\s*,\s*(\{[\s\S]*?\})\s*,?\s*\)",
)
_WS_TYPE_LITERAL_RE = re.compile(
    r"[\"']type[\"']\s*:\s*[\"']([^\"']+)[\"']",
)
_BROADCAST_CALL_RE = re.compile(
    r"(?:websocket_broadcast|_broadcast_websocket_message|_broadcast_to_websocket_clients)\s*\(",
)


def extract_client_inbound_types(meshchat_py: Path) -> list[str]:
    text = meshchat_py.read_text(encoding="utf-8")
    start = text.find("async def on_websocket_data_received")
    if start < 0:
        return []
    end = text.find("\n    async def ", start + 1)
    if end < 0:
        end = text.find("\n    def ", start + 1)
    block = text[start:end] if end > start else text[start:]
    types = _CLIENT_HANDLER_RE.findall(block)
    return sorted(set(types))


def _extract_type_literals_from_dict_literal(blob: str) -> str | None:
    match = re.search(r"[\"']type[\"']\s*:\s*[\"']([^\"']+)[\"']", blob)
    return match.group(1) if match else None


def extract_client_direct_response_types(meshchat_py: Path) -> list[str]:
    text = meshchat_py.read_text(encoding="utf-8")
    # Include rns.link.* helpers that live immediately after the WS dispatcher.
    start = text.find("async def on_websocket_data_received")
    if start < 0:
        return []
    end = text.find("\n    async def websocket_broadcast", start + 1)
    if end < 0:
        end = text.find("\n    async def ", start + 1)
    block = text[start:end] if end > start else text[start:]
    types: set[str] = set()
    for blob in _WS_SEND_STR_RE.findall(block):
        msg_type = _extract_type_literals_from_dict_literal(blob)
        if msg_type:
            types.add(msg_type)
    for blob in _RNS_LINK_SEND_RE.findall(block):
        msg_type = _extract_type_literals_from_dict_literal(blob)
        if msg_type:
            types.add(msg_type)
    return sorted(types)


def extract_server_broadcast_types(meshchat_py: Path) -> list[str]:
    text = meshchat_py.read_text(encoding="utf-8")
    types: set[str] = set()
    for match in _BROADCAST_CALL_RE.finditer(text):
        chunk = text[match.end() : match.end() + 1200]
        type_match = _WS_TYPE_LITERAL_RE.search(chunk)
        if type_match:
            types.add(type_match.group(1))
    link_manager = meshchat_py.parent / "src" / "backend" / "rns_link_manager.py"
    if link_manager.is_file():
        link_text = link_manager.read_text(encoding="utf-8")
        for type_match in _WS_TYPE_LITERAL_RE.finditer(link_text):
            msg_type = type_match.group(1)
            if msg_type.startswith("rns.link."):
                types.add(msg_type)
    for fn_name in ("send_config_to_websocket_clients",):
        start = text.find(f"async def {fn_name}")
        if start < 0:
            continue
        end = text.find("\n    async def ", start + 1)
        block = text[start:end] if end > start else text[start : start + 6000]
        for type_match in _WS_TYPE_LITERAL_RE.finditer(block):
            types.add(type_match.group(1))
    return sorted(types)


def load_ws_manifest(fixture_path: Path) -> dict[str, list[str]]:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    for key in ("client_inbound", "client_direct_responses", "server_broadcast"):
        data[key] = sorted(data.get(key, []))
    return data


def write_ws_manifest(fixture_path: Path, manifest: dict[str, list[str]]) -> None:
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {
        "client_inbound": sorted(manifest.get("client_inbound", [])),
        "client_direct_responses": sorted(manifest.get("client_direct_responses", [])),
        "server_broadcast": sorted(manifest.get("server_broadcast", [])),
    }
    fixture_path.write_text(
        json.dumps(ordered, indent=2) + "\n",
        encoding="utf-8",
    )
