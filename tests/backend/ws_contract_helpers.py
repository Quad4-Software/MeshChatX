# SPDX-License-Identifier: 0BSD

"""Helpers for WebSocket JSON message contract checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

_CLIENT_HANDLER_RE = re.compile(
    r"(?:if|elif)\s+_type\s*==\s*(?:[\"']([^\"']+)[\"']|WsInboundType\.([A-Z0-9_]+))",
)
_WS_SEND_STR_RE = re.compile(
    r"client\.send_str\s*\(\s*json\.dumps\s*\(\s*(\{[\s\S]*?\})\s*,?\s*\)",
)
_RNS_LINK_SEND_RE = re.compile(
    r"_rns_link_send\s*\(\s*client\s*,\s*(\{[\s\S]*?\})\s*,?\s*\)",
)
_WS_TYPE_LITERAL_RE = re.compile(
    r"[\"']type[\"']\s*:\s*(?:[\"']([^\"']+)[\"']|WsInboundType\.([A-Z0-9_]+))",
)
_WS_HANDLER_KEY_RE = re.compile(
    r"(?:[\"']([a-z0-9_.]+)[\"']|WsInboundType\.([A-Z0-9_]+))\s*:",
)
_WS_ENUM_MEMBER_RE = re.compile(
    r"^\s{4}([A-Z0-9_]+)\s*=\s*[\"']([^\"']+)[\"']\s*$",
    re.MULTILINE,
)
_BROADCAST_CALL_RE = re.compile(
    r"(?:websocket_broadcast|_broadcast_websocket_message|_broadcast_to_websocket_clients)\s*\(",
)
_DISPATCH_MARKERS = (
    "async def on_websocket_data_received",
    "async def dispatch_websocket_data",
)


def ws_inbound_type_values(repo_root: Path) -> dict[str, str]:
    """Return {member_name: wire value} for WsInboundType in constants.py."""
    path = repo_root / "meshchatx" / "src" / "backend" / "constants.py"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    start = text.find("class WsInboundType")
    if start < 0:
        return {}
    end = text.find("\n\n\n", start)
    block = text[start:end] if end > start else text[start:]
    return dict(_WS_ENUM_MEMBER_RE.findall(block))


def _resolve_ws_key(match: re.Match, members: dict[str, str]) -> str | None:
    literal, member = match.group(1), match.group(2)
    if literal is not None:
        return literal
    return members.get(member)


def iter_ws_source_files(repo_root: Path) -> list[Path]:
    """Return Python sources that may define WS inbound or outbound types."""
    files: list[Path] = []
    meshchat_py = repo_root / "meshchatx" / "meshchat.py"
    if meshchat_py.is_file():
        files.append(meshchat_py)
    http_root = repo_root / "meshchatx" / "src" / "backend" / "http"
    if http_root.is_dir():
        files.extend(sorted(http_root.rglob("*.py")))
    lifecycle_root = repo_root / "meshchatx" / "src" / "backend" / "lifecycle"
    if lifecycle_root.is_dir():
        files.extend(sorted(lifecycle_root.rglob("*.py")))
    link_manager = repo_root / "meshchatx" / "src" / "backend" / "rns_link_manager.py"
    if link_manager.is_file():
        files.append(link_manager)
    return files


def _repo_root_from_meshchat_py(meshchat_py: Path) -> Path:
    meshchat_py = Path(meshchat_py)
    if meshchat_py.name == "meshchat.py":
        return meshchat_py.parent.parent
    for parent in [meshchat_py, *meshchat_py.parents]:
        candidate = parent / "meshchatx" / "meshchat.py"
        if candidate.is_file():
            return parent
    return meshchat_py.parent.parent


def _dispatcher_block(text: str) -> str:
    start = -1
    for marker in _DISPATCH_MARKERS:
        start = text.find(marker)
        if start >= 0:
            break
    if start < 0:
        return ""
    end = text.find("\n    async def ", start + 1)
    if end < 0:
        end = text.find("\n    def ", start + 1)
    if end < 0:
        end = text.find("\ndef ", start + 1)
    return text[start:end] if end > start else text[start:]


def _direct_response_block(text: str) -> str:
    start = -1
    for marker in _DISPATCH_MARKERS:
        start = text.find(marker)
        if start >= 0:
            break
    if start < 0:
        return ""
    end = text.find("\n    async def websocket_broadcast", start + 1)
    if end < 0:
        end = text.find("\nasync def websocket_broadcast", start + 1)
    if end < 0:
        end = text.find("\n    async def ", start + 1)
    if end < 0:
        end = text.find("\nasync def ", start + 1)
    return text[start:end] if end > start else text[start:]


def extract_client_inbound_types(meshchat_py: Path) -> list[str]:
    repo_root = _repo_root_from_meshchat_py(meshchat_py)
    types: set[str] = set()
    members = ws_inbound_type_values(repo_root)
    for path in iter_ws_source_files(repo_root):
        if path.name == "rns_link_manager.py":
            continue
        text = path.read_text(encoding="utf-8")
        block = _dispatcher_block(text)
        if block:
            for m in _CLIENT_HANDLER_RE.finditer(block):
                resolved = _resolve_ws_key(m, members)
                if resolved:
                    types.add(resolved)
        if "backend/http" not in path.as_posix():
            continue
        if not block:
            for m in _CLIENT_HANDLER_RE.finditer(text):
                resolved = _resolve_ws_key(m, members)
                if resolved:
                    types.add(resolved)
        # Only keys inside HANDLERS / WS_HANDLERS / HANDLER_REGISTRY dict literals.
        for reg_name in ("HANDLERS", "WS_HANDLERS", "HANDLER_REGISTRY", "ws_handlers"):
            for reg_match in re.finditer(
                rf"^{reg_name}\s*=\s*\{{",
                text,
                re.MULTILINE,
            ):
                brace = text.find("{", reg_match.start())
                depth = 0
                i = brace
                while i < len(text):
                    ch = text[i]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            blob = text[brace : i + 1]
                            for match in _WS_HANDLER_KEY_RE.finditer(blob):
                                resolved = _resolve_ws_key(match, members)
                                if resolved:
                                    types.add(resolved)
                            break
                    i += 1
    return sorted(types)


def _extract_type_literals_from_dict_literal(
    blob: str,
    members: dict[str, str],
) -> str | None:
    match = _WS_TYPE_LITERAL_RE.search(blob)
    if not match:
        return None
    return _resolve_ws_key(match, members)


def extract_client_direct_response_types(meshchat_py: Path) -> list[str]:
    repo_root = _repo_root_from_meshchat_py(meshchat_py)
    members = ws_inbound_type_values(repo_root)
    types: set[str] = set()
    for path in iter_ws_source_files(repo_root):
        if path.name == "rns_link_manager.py":
            continue
        text = path.read_text(encoding="utf-8")
        block = _direct_response_block(text)
        scan = block or text
        if not block and "backend/http" not in path.as_posix():
            continue
        for blob in _WS_SEND_STR_RE.findall(scan):
            msg_type = _extract_type_literals_from_dict_literal(blob, members)
            if msg_type:
                types.add(msg_type)
        for blob in _RNS_LINK_SEND_RE.findall(scan):
            msg_type = _extract_type_literals_from_dict_literal(blob, members)
            if msg_type:
                types.add(msg_type)
    return sorted(types)


def extract_server_broadcast_types(meshchat_py: Path) -> list[str]:
    repo_root = _repo_root_from_meshchat_py(meshchat_py)
    members = ws_inbound_type_values(repo_root)
    types: set[str] = set()
    for path in iter_ws_source_files(repo_root):
        text = path.read_text(encoding="utf-8")
        for match in _BROADCAST_CALL_RE.finditer(text):
            chunk = text[match.end() : match.end() + 1200]
            type_match = _WS_TYPE_LITERAL_RE.search(chunk)
            if type_match:
                resolved = _resolve_ws_key(type_match, members)
                if resolved:
                    types.add(resolved)
        if path.name == "rns_link_manager.py":
            for type_match in _WS_TYPE_LITERAL_RE.finditer(text):
                msg_type = _resolve_ws_key(type_match, members)
                if msg_type and msg_type.startswith("rns.link."):
                    types.add(msg_type)
        for fn_name in ("send_config_to_websocket_clients",):
            start = text.find(f"async def {fn_name}")
            if start < 0:
                continue
            end = text.find("\n    async def ", start + 1)
            if end < 0:
                end = text.find("\nasync def ", start + 1)
            block = text[start:end] if end > start else text[start : start + 6000]
            for type_match in _WS_TYPE_LITERAL_RE.finditer(block):
                resolved = _resolve_ws_key(type_match, members)
                if resolved:
                    types.add(resolved)
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
