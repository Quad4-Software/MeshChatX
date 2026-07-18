# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import os
import zipfile

MAX_PLUGIN_ZIP_BYTES = 20 * 1024 * 1024
MAX_EXTRACT_BYTES = 50 * 1024 * 1024
MAX_EXTRACT_FILES = 256
MAX_WASM_BYTES = 10 * 1024 * 1024
MAX_INVOKE_PAYLOAD_BYTES = 65_536
PLUGIN_ERROR_BUDGET = 5
PLUGIN_ERROR_WINDOW_SECONDS = 300


class PluginSecurityError(ValueError):
    """Raised when a plugin archive or asset fails validation."""


def normalize_asset_path(asset_name: str) -> str:
    if not isinstance(asset_name, str) or "\x00" in asset_name:
        raise PluginSecurityError("invalid asset path")
    normalized = os.path.normpath(asset_name).replace("\\", "/")
    if not normalized or normalized in {".", ".."}:
        raise PluginSecurityError("invalid asset path")
    if normalized.startswith("../") or normalized.startswith("/"):
        raise PluginSecurityError("invalid asset path")
    if "/../" in f"/{normalized}/":
        raise PluginSecurityError("invalid asset path")
    # Reject Windows drive-absolute forms (C:/...) that can escape on win32 joins.
    if ":" in normalized:
        raise PluginSecurityError("invalid asset path")
    return normalized


def validate_wasm_file(path: str) -> None:
    if not os.path.isfile(path):
        raise PluginSecurityError("backend wasm entry not found")
    size = os.path.getsize(path)
    if size <= 0:
        raise PluginSecurityError("backend wasm entry is empty")
    if size > MAX_WASM_BYTES:
        raise PluginSecurityError("backend wasm entry is too large")


def validate_invoke_payload(payload: bytes) -> None:
    if len(payload) > MAX_INVOKE_PAYLOAD_BYTES:
        raise PluginSecurityError("plugin invoke payload is too large")


def _zip_entry_is_safe(name: str) -> bool:
    if not isinstance(name, str) or "\x00" in name:
        return False
    normalized = os.path.normpath(name).replace("\\", "/")
    if normalized.startswith("../") or normalized.startswith("/"):
        return False
    if normalized in {"", ".", ".."}:
        return False
    if ":" in normalized:
        return False
    if "/../" in f"/{normalized}/":
        return False
    return True


def safe_extract_zip(zip_path: str, extract_dir: str) -> str:
    total_bytes = 0
    file_count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if not _zip_entry_is_safe(info.filename):
                raise PluginSecurityError("plugin archive contains unsafe paths")
            total_bytes += info.file_size
            file_count += 1
            if file_count > MAX_EXTRACT_FILES:
                raise PluginSecurityError("plugin archive contains too many files")
            if total_bytes > MAX_EXTRACT_BYTES:
                raise PluginSecurityError("plugin archive is too large when extracted")
        archive.extractall(extract_dir)
    return resolve_plugin_root(extract_dir)


def resolve_plugin_root(extract_dir: str) -> str:
    manifest_path = os.path.join(extract_dir, "plugin.json")
    if os.path.isfile(manifest_path):
        return extract_dir
    children = [
        name
        for name in os.listdir(extract_dir)
        if os.path.isdir(os.path.join(extract_dir, name))
    ]
    if len(children) == 1:
        candidate = os.path.join(extract_dir, children[0])
        if os.path.isfile(os.path.join(candidate, "plugin.json")):
            return candidate
    raise PluginSecurityError("plugin.json not found in archive")


def validate_zip_bytes(payload: bytes) -> None:
    if not payload:
        raise PluginSecurityError("empty plugin archive")
    if len(payload) > MAX_PLUGIN_ZIP_BYTES:
        raise PluginSecurityError("plugin archive is too large")
    if not payload.startswith(b"PK"):
        raise PluginSecurityError("plugin archive is not a zip file")
