# SPDX-License-Identifier: 0BSD

"""Single-file WASM plugin bundles with embedded manifest/files/signature."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

WASM_MAGIC = b"\x00asm"
WASM_VERSION = b"\x01\x00\x00\x00"
WASM_SECTION_CUSTOM = 0

SECTION_PLUGIN = "meshchatx.plugin"
SECTION_FILES = "meshchatx.files"
SECTION_SIGNATURE = "meshchatx.signature"


def is_wasm_bytes(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == WASM_MAGIC


MAX_WASM_BUNDLE_BYTES = 32 * 1024 * 1024
MAX_WASM_EMBEDDED_FILE = 8 * 1024 * 1024
MAX_WASM_EMBEDDED_KEYS = 64


@dataclass
class WasmBundle:
    manifest: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    wasm_binary: bytes = b""
    signature: bytes = b""


def read_uleb32(data: bytes) -> tuple[int, int]:
    result = 0
    shift = 0
    for index, byte in enumerate(data):
        if shift >= 35:
            raise ValueError("invalid uleb32")
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return result, index + 1
        shift += 7
    raise ValueError("truncated uleb32")


def encode_uleb32(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value != 0:
            byte |= 0x80
        out.append(byte)
        if value == 0:
            break
    return bytes(out)


def read_byte_vector(data: bytes) -> tuple[bytes, bytes]:
    size, consumed = read_uleb32(data)
    end = consumed + size
    if end > len(data):
        raise ValueError("truncated byte vector")
    return data[consumed:end], data[end:]


def encode_byte_vector(data: bytes) -> bytes:
    return encode_uleb32(len(data)) + data


def append_custom_section(wasm: bytes, name: str, data: bytes) -> bytes:
    if not name:
        raise ValueError("custom section name is required")
    payload = encode_byte_vector(name.encode("utf-8")) + encode_byte_vector(data)
    section = bytes([WASM_SECTION_CUSTOM]) + encode_uleb32(len(payload)) + payload
    return wasm + section


def parse_wasm_bundle(data: bytes) -> WasmBundle:
    if len(data) < 8 or data[:4] != WASM_MAGIC:
        raise ValueError("invalid wasm module")
    if data[4:8] != WASM_VERSION:
        raise ValueError("unsupported wasm version")
    bundle = WasmBundle(wasm_binary=data, files={})
    offset = 8
    while offset < len(data):
        section_id = data[offset]
        offset += 1
        size, n = read_uleb32(data[offset:])
        offset += n
        if size > len(data) - offset:
            raise ValueError("truncated wasm section")
        payload = data[offset : offset + size]
        offset += size
        if section_id != WASM_SECTION_CUSTOM:
            continue
        try:
            name_bytes, rest = read_byte_vector(payload)
            content, _ = read_byte_vector(rest)
        except ValueError:
            continue
        name = name_bytes.decode("utf-8", errors="replace")
        if name == SECTION_PLUGIN:
            manifest = json.loads(content.decode("utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("embedded manifest must be an object")
            bundle.manifest = manifest
        elif name == SECTION_FILES:
            files = json.loads(content.decode("utf-8"))
            if not isinstance(files, dict):
                raise ValueError("embedded files must be an object")
            for key, value in files.items():
                if isinstance(key, str) and isinstance(value, str):
                    bundle.files[key] = value
        elif name == SECTION_SIGNATURE:
            bundle.signature = bytes(content)
    return bundle


def wasm_payload_without_signature(data: bytes) -> bytes:
    if len(data) < 8 or data[:4] != WASM_MAGIC:
        raise ValueError("invalid wasm module")
    if data[4:8] != WASM_VERSION:
        raise ValueError("unsupported wasm version")
    out = bytearray(data[:8])
    offset = 8
    while offset < len(data):
        section_start = offset
        section_id = data[offset]
        offset += 1
        size, n = read_uleb32(data[offset:])
        offset += n
        if size > len(data) - offset:
            raise ValueError("truncated wasm section")
        payload = data[offset : offset + size]
        offset += size
        if section_id != WASM_SECTION_CUSTOM:
            out.extend(data[section_start:offset])
            continue
        try:
            name_bytes, _rest = read_byte_vector(payload)
        except ValueError:
            out.extend(data[section_start:offset])
            continue
        name = name_bytes.decode("utf-8", errors="replace")
        if name == SECTION_SIGNATURE:
            continue
        out.extend(data[section_start:offset])
    return bytes(out)


def append_wasm_signature(wasm: bytes, signature: bytes) -> bytes:
    if not signature:
        raise ValueError("signature is required")
    payload = wasm_payload_without_signature(wasm)
    return append_custom_section(payload, SECTION_SIGNATURE, signature)


def validate_embedded_path(name: str) -> None:
    clean = os.path.normpath(name.replace("\\", "/")).replace("\\", "/")
    if clean in {"", "."} or clean.startswith("..") or clean.startswith("/"):
        raise ValueError(f"invalid embedded path {name!r}")


def validate_embedded_bundle(bundle: WasmBundle) -> None:
    if len(bundle.wasm_binary) > MAX_WASM_BUNDLE_BYTES:
        raise ValueError("wasm bundle is too large")
    if len(bundle.files) > MAX_WASM_EMBEDDED_KEYS:
        raise ValueError("too many embedded files")
    for name, content in bundle.files.items():
        validate_embedded_path(name)
        if len(content.encode("utf-8")) > MAX_WASM_EMBEDDED_FILE:
            raise ValueError(f"embedded file {name!r} too large")


def bundle_wasm(
    wasm: bytes,
    manifest: dict[str, Any],
    files: dict[str, str] | None = None,
) -> bytes:
    if len(wasm) < 8 or wasm[:4] != WASM_MAGIC:
        raise ValueError("invalid wasm module")
    if len(wasm) > MAX_WASM_BUNDLE_BYTES:
        raise ValueError("wasm module too large")
    if not isinstance(manifest, dict) or not str(manifest.get("id") or "").strip():
        raise ValueError("manifest id is required")
    files = files or {}
    if len(files) > MAX_WASM_EMBEDDED_KEYS:
        raise ValueError("too many embedded files")
    out = bytes(wasm)
    out = append_custom_section(
        out,
        SECTION_PLUGIN,
        json.dumps(manifest, separators=(",", ":")).encode("utf-8"),
    )
    if files:
        for name, content in files.items():
            validate_embedded_path(name)
            if len(content.encode("utf-8")) > MAX_WASM_EMBEDDED_FILE:
                raise ValueError(f"embedded file {name!r} too large")
        out = append_custom_section(
            out,
            SECTION_FILES,
            json.dumps(files, separators=(",", ":")).encode("utf-8"),
        )
    if len(out) > MAX_WASM_BUNDLE_BYTES:
        raise ValueError("bundled wasm module too large")
    return out


def _strip_bundle_metadata_sections(data: bytes) -> bytes:
    if len(data) < 8 or data[:4] != WASM_MAGIC:
        return data
    metadata_names = {SECTION_PLUGIN, SECTION_FILES, SECTION_SIGNATURE}
    out = bytearray(data[:8])
    offset = 8
    while offset < len(data):
        section_start = offset
        section_id = data[offset]
        offset += 1
        size, n = read_uleb32(data[offset:])
        offset += n
        if size > len(data) - offset:
            break
        payload = data[offset : offset + size]
        offset += size
        if section_id != WASM_SECTION_CUSTOM:
            out.extend(data[section_start:offset])
            continue
        try:
            name_bytes, _rest = read_byte_vector(payload)
            name = name_bytes.decode("utf-8", errors="replace")
        except ValueError:
            out.extend(data[section_start:offset])
            continue
        if name in metadata_names:
            continue
        out.extend(data[section_start:offset])
    return bytes(out)


def write_wasm_bundle(dest: str, bundle: WasmBundle) -> None:
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "plugin.json"), "w", encoding="utf-8") as handle:
        json.dump(bundle.manifest, handle, indent=2)
        handle.write("\n")
    backend = bundle.manifest.get("backend") or {}
    backend_entry = ""
    if isinstance(backend, dict):
        backend_entry = str(backend.get("entry") or "").strip()
    if not backend_entry:
        backend_entry = "backend/plugin.wasm"
    backend_path = os.path.join(dest, backend_entry.replace("\\", "/"))
    os.makedirs(os.path.dirname(backend_path) or dest, exist_ok=True)
    runtime_wasm = _strip_bundle_metadata_sections(
        wasm_payload_without_signature(bundle.wasm_binary)
    )
    with open(backend_path, "wb") as handle:
        handle.write(runtime_wasm)
    for name, content in bundle.files.items():
        if name.replace("\\", "/") == backend_entry.replace("\\", "/"):
            continue
        validate_embedded_path(name)
        file_path = os.path.join(dest, name.replace("\\", "/"))
        os.makedirs(os.path.dirname(file_path) or dest, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(content)
