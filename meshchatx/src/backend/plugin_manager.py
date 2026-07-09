# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, cast

from meshchatx.src.backend.plugin_guard import (
    PLUGIN_ERROR_BUDGET,
    PLUGIN_ERROR_WINDOW_SECONDS,
    PluginSecurityError,
    normalize_asset_path,
    safe_extract_zip,
    validate_invoke_payload,
    validate_wasm_file,
    validate_zip_bytes,
)
from meshchatx.src.backend.plugin_permissions import (
    collect_network_endpoints,
    declared_permission_ids,
    deserialize_granted,
    granted_allows_hook,
    granted_allows_manager,
    granted_allows_network_fetch,
    granted_allows_storage,
    normalize_granted_permissions,
    normalize_network_mode,
    requires_network_fetch,
    serialize_granted,
    validate_declared_permissions,
)

SUPPORTED_API_VERSION = 1
PLUGIN_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")

MINIMAL_PLUGIN_WAT = """
(module
  (import "host" "log" (func (param i32 i32)))
  (memory (export "memory") 1)
  (func (export "on_hook") (param i32 i32) (result i32)
    i32.const 0
  )
  (func (export "invoke") (param i32 i32 i32) (result i32)
    i32.const 0
  )
)
""".strip()


@dataclass
class PluginRecord:
    id: str
    version: str
    manifest: dict[str, Any]
    enabled: bool
    install_path: str
    auto_disabled_reason: str | None = None
    granted_permissions: list[str] | None = None
    announce_handlers: list[Any] = field(default_factory=list)
    error_count: int = 0
    last_error_at: float = 0.0


class PluginManager:
    """Discover, install, and execute MeshChatX plugins."""

    def __init__(self, storage_dir: str, app: Any | None = None):
        self.storage_dir = os.path.join(storage_dir, "plugins")
        self.installed_dir = os.path.join(self.storage_dir, "installed")
        self.state_db_path = os.path.join(self.storage_dir, "plugin_state.db")
        self.app = app
        self._lock = threading.RLock()
        self._plugins: dict[str, PluginRecord] = {}
        self._wasmtime = None
        os.makedirs(self.installed_dir, exist_ok=True)
        self._init_state_db()
        self._load_installed_plugins()

    def _init_state_db(self) -> None:
        with sqlite3.connect(self.state_db_path) as conn:
            conn.execute(
                """
        CREATE TABLE IF NOT EXISTS plugin_storage (
          plugin_id TEXT NOT NULL,
          storage_key TEXT NOT NULL,
          storage_value TEXT NOT NULL,
          PRIMARY KEY (plugin_id, storage_key)
        )
        """
            )
            conn.execute(
                """
        CREATE TABLE IF NOT EXISTS plugin_state (
          plugin_id TEXT PRIMARY KEY,
          enabled INTEGER NOT NULL DEFAULT 0,
          auto_disabled_reason TEXT,
          granted_permissions TEXT
        )
        """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(plugin_state)").fetchall()
            }
            if "granted_permissions" not in columns:
                conn.execute(
                    "ALTER TABLE plugin_state ADD COLUMN granted_permissions TEXT"
                )
            conn.commit()

    def set_app(self, app: Any) -> None:
        self.app = app

    def _plugins_runtime_enabled(self) -> bool:
        if self.app is None:
            return True
        return bool(getattr(self.app, "plugins_enabled", True))

    def _require_runtime_enabled(self) -> None:
        if not self._plugins_runtime_enabled():
            raise PermissionError("plugins are disabled")

    def _load_wasmtime(self):
        if self._wasmtime is not None:
            return self._wasmtime
        try:
            import wasmtime
        except ImportError as exc:
            raise RuntimeError("wasmtime is required for backend plugins") from exc
        self._wasmtime = wasmtime
        return wasmtime

    def _load_installed_plugins(self) -> None:
        if not os.path.isdir(self.installed_dir):
            return
        for entry in sorted(os.listdir(self.installed_dir)):
            plugin_dir = os.path.join(self.installed_dir, entry)
            manifest_path = os.path.join(plugin_dir, "plugin.json")
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, encoding="utf-8") as handle:
                    manifest = json.load(handle)
                manifest = self._validate_manifest(manifest)
                enabled, auto_disabled_reason, granted = self._read_plugin_state(
                    manifest["id"]
                )
                declared = declared_permission_ids(manifest)
                if granted is None:
                    granted = list(declared)
                else:
                    granted = normalize_granted_permissions(declared, granted)
                self._plugins[manifest["id"]] = PluginRecord(
                    id=manifest["id"],
                    version=manifest["version"],
                    manifest=manifest,
                    enabled=enabled,
                    install_path=plugin_dir,
                    auto_disabled_reason=auto_disabled_reason,
                    granted_permissions=granted,
                )
            except Exception as exc:
                print(f"Failed to load plugin from {plugin_dir}: {exc}")

    def _read_plugin_state(
        self, plugin_id: str
    ) -> tuple[bool, str | None, list[str] | None]:
        with sqlite3.connect(self.state_db_path) as conn:
            row = conn.execute(
                """
        SELECT enabled, auto_disabled_reason, granted_permissions
        FROM plugin_state WHERE plugin_id = ?
        """,
                (plugin_id,),
            ).fetchone()
        if not row:
            return False, None, None
        return bool(row[0]), row[1], deserialize_granted(row[2])

    def _write_plugin_state(
        self,
        plugin_id: str,
        enabled: bool,
        auto_disabled_reason: str | None = None,
        granted_permissions: list[str] | None = None,
    ) -> None:
        with sqlite3.connect(self.state_db_path) as conn:
            conn.execute(
                """
        INSERT INTO plugin_state (
          plugin_id, enabled, auto_disabled_reason, granted_permissions
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(plugin_id) DO UPDATE SET
          enabled = excluded.enabled,
          auto_disabled_reason = excluded.auto_disabled_reason,
          granted_permissions = COALESCE(
            excluded.granted_permissions,
            plugin_state.granted_permissions
          )
        """,
                (
                    plugin_id,
                    1 if enabled else 0,
                    auto_disabled_reason,
                    None
                    if granted_permissions is None
                    else serialize_granted(granted_permissions),
                ),
            )
            conn.commit()

    def _validate_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(manifest, dict):
            raise ValueError("plugin manifest must be an object")
        plugin_id = manifest.get("id")
        if not isinstance(plugin_id, str) or not PLUGIN_ID_RE.match(plugin_id):
            raise ValueError("plugin id is invalid")
        version = manifest.get("version")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("plugin version is required")
        api_version = manifest.get("apiVersion")
        if api_version is None:
            raise ValueError("plugin apiVersion is required")
        try:
            parsed_api_version = int(api_version)
        except (TypeError, ValueError) as exc:
            raise ValueError("plugin apiVersion is invalid") from exc
        if parsed_api_version != SUPPORTED_API_VERSION:
            raise ValueError(
                f"unsupported apiVersion (expected {SUPPORTED_API_VERSION})"
            )
        validate_declared_permissions(manifest)
        return manifest

    def list_plugins(self) -> list[dict[str, Any]]:
        if not self._plugins_runtime_enabled():
            return []
        with self._lock:
            rows = []
            for record in self._plugins.values():
                rows.append(self._public_plugin_view(record))
            rows.sort(key=lambda item: item["id"])
            return rows

    def get_plugin(self, plugin_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._plugins.get(plugin_id)
            if not record:
                return None
            return self._public_plugin_view(record)

    def _public_plugin_view(self, record: PluginRecord) -> dict[str, Any]:
        manifest = record.manifest
        permissions = manifest.get("permissions") or {}
        declared = declared_permission_ids(manifest)
        granted = record.granted_permissions
        if granted is None:
            granted = list(declared)
        endpoints = collect_network_endpoints(manifest, record.install_path)
        return {
            "id": record.id,
            "version": record.version,
            "name": manifest.get("name") or record.id,
            "description": manifest.get("description") or "",
            "enabled": record.enabled,
            "auto_disabled_reason": record.auto_disabled_reason,
            "manifest": manifest,
            "permissions": permissions,
            "declared_permissions": declared,
            "granted_permissions": granted,
            "network_endpoints": endpoints,
            "requires_network_fetch": requires_network_fetch(manifest, endpoints),
            "contributes": manifest.get("contributes") or {},
            "has_frontend": bool(manifest.get("frontend")),
            "has_backend": bool(manifest.get("backend")),
        }

    def _build_preview_from_directory(self, source_dir: str) -> dict[str, Any]:
        manifest_path = os.path.join(source_dir, "plugin.json")
        if not os.path.isfile(manifest_path):
            raise ValueError("plugin.json not found")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = self._validate_manifest(json.load(handle))
        declared = declared_permission_ids(manifest)
        endpoints = collect_network_endpoints(manifest, source_dir)
        network_mode = normalize_network_mode(
            (manifest.get("permissions") or {}).get("network")
        )
        return {
            "id": manifest["id"],
            "name": manifest.get("name") or manifest["id"],
            "version": manifest["version"],
            "description": manifest.get("description") or "",
            "permissions": declared,
            "network_endpoints": endpoints,
            "requires_network_fetch": requires_network_fetch(manifest, endpoints),
            "network_mode": network_mode,
            "has_frontend": bool(manifest.get("frontend")),
            "has_backend": bool(manifest.get("backend")),
            "manifest": manifest,
        }

    def preview_from_zip_bytes(self, payload: bytes) -> dict[str, Any]:
        import tempfile

        self._require_runtime_enabled()
        validate_zip_bytes(payload)
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = os.path.join(tmp, "plugin.zip")
            with open(zip_path, "wb") as handle:
                handle.write(payload)
            extract_dir = os.path.join(tmp, "extract")
            os.makedirs(extract_dir, exist_ok=True)
            plugin_root = safe_extract_zip(zip_path, extract_dir)
            return self._build_preview_from_directory(plugin_root)

    def install_from_directory(
        self,
        source_dir: str,
        granted_permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        self._require_runtime_enabled()
        manifest_path = os.path.join(source_dir, "plugin.json")
        if not os.path.isfile(manifest_path):
            raise ValueError("plugin.json not found")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = self._validate_manifest(json.load(handle))
        plugin_id = manifest["id"]
        declared = declared_permission_ids(manifest)
        granted = normalize_granted_permissions(declared, granted_permissions)
        target_dir = os.path.join(self.installed_dir, plugin_id)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        with self._lock:
            enabled, auto_disabled_reason, _existing_granted = self._read_plugin_state(
                plugin_id
            )
            self._write_plugin_state(
                plugin_id,
                enabled,
                auto_disabled_reason,
                granted_permissions=granted,
            )
            self._plugins[plugin_id] = PluginRecord(
                id=plugin_id,
                version=manifest["version"],
                manifest=manifest,
                enabled=enabled,
                install_path=target_dir,
                auto_disabled_reason=auto_disabled_reason,
                granted_permissions=granted,
            )
            return self._public_plugin_view(self._plugins[plugin_id])

    def install_from_zip_bytes(
        self,
        payload: bytes,
        granted_permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        import tempfile

        validate_zip_bytes(payload)
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = os.path.join(tmp, "plugin.zip")
            with open(zip_path, "wb") as handle:
                handle.write(payload)
            extract_dir = os.path.join(tmp, "extract")
            os.makedirs(extract_dir, exist_ok=True)
            plugin_root = safe_extract_zip(zip_path, extract_dir)
            return self.install_from_directory(
                plugin_root, granted_permissions=granted_permissions
            )

    def enable(self, plugin_id: str) -> dict[str, Any]:
        self._require_runtime_enabled()
        with self._lock:
            record = self._require_plugin(plugin_id)
            self._validate_plugin_runtime(record)
            record.enabled = True
            record.auto_disabled_reason = None
            record.error_count = 0
            record.last_error_at = 0.0
            self._write_plugin_state(plugin_id, True, None)
            self._register_plugin_hooks(record)
            return self._public_plugin_view(record)

    def disable(self, plugin_id: str, reason: str | None = None) -> dict[str, Any]:
        with self._lock:
            record = self._require_plugin(plugin_id)
            record.enabled = False
            if reason:
                record.auto_disabled_reason = reason
            self._write_plugin_state(plugin_id, False, record.auto_disabled_reason)
            self._unregister_plugin_hooks(record)
            if reason:
                self._broadcast_plugin_event(
                    plugin_id, "plugin.disabled", {"reason": reason}
                )
            return self._public_plugin_view(record)

    def remove(self, plugin_id: str) -> None:
        with self._lock:
            record = self._plugins.pop(plugin_id, None)
            if record:
                self._unregister_plugin_hooks(record)
            target_dir = os.path.join(self.installed_dir, plugin_id)
            if os.path.isdir(target_dir):
                shutil.rmtree(target_dir)
            with sqlite3.connect(self.state_db_path) as conn:
                conn.execute(
                    "DELETE FROM plugin_state WHERE plugin_id = ?", (plugin_id,)
                )
                conn.execute(
                    "DELETE FROM plugin_storage WHERE plugin_id = ?", (plugin_id,)
                )
                conn.commit()

    def asset_path(self, plugin_id: str, asset_name: str) -> str:
        self._require_runtime_enabled()
        record = self._require_plugin(plugin_id)
        normalized = normalize_asset_path(asset_name)
        path = os.path.join(record.install_path, normalized)
        if not os.path.isfile(path):
            raise FileNotFoundError(asset_name)
        return path

    def locale_path(self, plugin_id: str, locale: str) -> str | None:
        record = self._require_plugin(plugin_id)
        i18n = record.manifest.get("i18n") or {}
        directory = i18n.get("directory") or "locales"
        default_locale = i18n.get("defaultLocale") or "en"
        candidates = []
        for code in (locale, default_locale, "en"):
            if code and code not in candidates:
                candidates.append(code)
        for code in candidates:
            relative = os.path.join(directory, f"{code}.json").replace("\\", "/")
            path = os.path.join(record.install_path, relative)
            if os.path.isfile(path):
                return path
        return None

    def load_locale_messages(self, plugin_id: str, locale: str) -> dict[str, Any]:
        path = self.locale_path(plugin_id, locale)
        if not path:
            return {}
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("plugin locale file must be an object")
        return data

    def report_failure(
        self, plugin_id: str, reason: str, source: str = "frontend"
    ) -> dict[str, Any] | None:
        with self._lock:
            record = self._plugins.get(plugin_id)
            if not record:
                return None
            return self._record_plugin_failure(
                record, f"{source}: {reason}", auto_disable=True
            )

    def _require_plugin(self, plugin_id: str) -> PluginRecord:
        record = self._plugins.get(plugin_id)
        if not record:
            raise KeyError(f"plugin not found: {plugin_id}")
        return record

    def _permission_allowed(self, record: PluginRecord, capability: str) -> bool:
        permissions = record.manifest.get("permissions") or {}
        managers = permissions.get("managers") or []
        if capability not in managers:
            return False
        return granted_allows_manager(record.granted_permissions, capability)

    def _hook_allowed(self, record: PluginRecord, hook: str) -> bool:
        permissions = record.manifest.get("permissions") or {}
        hooks = permissions.get("hooks") or []
        if hook not in hooks:
            return False
        return granted_allows_hook(record.granted_permissions, hook)

    def _network_fetch_allowed(self, record: PluginRecord) -> bool:
        permissions = record.manifest.get("permissions") or {}
        network = normalize_network_mode(permissions.get("network"))
        if network != "fetch":
            return False
        return granted_allows_network_fetch(record.granted_permissions)

    def _storage_allowed(self, record: PluginRecord) -> bool:
        permissions = record.manifest.get("permissions") or {}
        storage = permissions.get("storage") or "none"
        if storage != "isolated":
            return False
        return granted_allows_storage(record.granted_permissions)

    def storage_get(self, plugin_id: str, key: str) -> str | None:
        record = self._require_plugin(plugin_id)
        if not self._storage_allowed(record):
            raise PermissionError("storage permission not granted")
        with sqlite3.connect(self.state_db_path) as conn:
            row = conn.execute(
                "SELECT storage_value FROM plugin_storage WHERE plugin_id = ? AND storage_key = ?",
                (plugin_id, key),
            ).fetchone()
        return row[0] if row else None

    def storage_set(self, plugin_id: str, key: str, value: str) -> None:
        record = self._require_plugin(plugin_id)
        if not self._storage_allowed(record):
            raise PermissionError("storage permission not granted")
        with sqlite3.connect(self.state_db_path) as conn:
            conn.execute(
                """
        INSERT INTO plugin_storage (plugin_id, storage_key, storage_value)
        VALUES (?, ?, ?)
        ON CONFLICT(plugin_id, storage_key) DO UPDATE SET storage_value = excluded.storage_value
        """,
                (plugin_id, key, value),
            )
            conn.commit()

    def network_fetch_allowed(self, plugin_id: str) -> bool:
        record = self._require_plugin(plugin_id)
        if not record.enabled:
            return False
        return self._network_fetch_allowed(record)

    def call_manager(
        self, plugin_id: str, capability: str, args: dict[str, Any]
    ) -> Any:
        record = self._require_plugin(plugin_id)
        if not record.enabled:
            raise PermissionError("plugin is disabled")
        if not self._permission_allowed(record, capability):
            raise PermissionError(f"capability not granted: {capability}")
        if capability == "destinationPath.read":
            return self._destination_path_read(args)
        if capability == "rnsLink.open":
            return self._rns_link_open(args)
        if capability == "rnsLink.identify":
            return self._rns_link_identify(args)
        if capability == "rnsLink.request":
            return self._rns_link_request(args)
        if capability == "rnsLink.send":
            return self._rns_link_send(args)
        if capability == "rnsLink.close":
            return self._rns_link_close(args)
        raise ValueError(f"unknown capability: {capability}")

    def _require_rns_link_manager(self):
        if not self.app:
            raise RuntimeError("app is not available")
        manager = getattr(self.app, "rns_link_manager", None)
        if manager is None:
            raise RuntimeError("rns_link_manager is not available")
        return manager

    @staticmethod
    def _parse_rns_link_args(args: dict[str, Any]) -> tuple[bytes, str]:
        dest_hex = args.get("destination_hash")
        aspect = args.get("aspect")
        if not isinstance(dest_hex, str) or not dest_hex:
            raise ValueError("destination_hash is required")
        if not isinstance(aspect, str) or not aspect:
            raise ValueError("aspect is required")
        try:
            return bytes.fromhex(dest_hex), aspect
        except ValueError as exc:
            raise ValueError("invalid destination_hash") from exc

    def _await_rns_link_coro(self, coro, *, timeout: float = 45.0):
        import asyncio

        from meshchatx.src.backend.async_utils import AsyncUtils

        loop = AsyncUtils.main_loop
        if loop is not None and loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=timeout)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError("event loop is not available")

    def _rns_link_open(self, args: dict[str, Any]) -> dict[str, Any]:
        dest_hash, aspect = self._parse_rns_link_args(args)
        manager = self._require_rns_link_manager()
        auto_identify = bool(args.get("auto_identify", False))
        link, identified, failure_reason = self._await_rns_link_coro(
            manager.open_link(
                dest_hash,
                aspect,
                auto_identify=auto_identify,
            )
        )
        if link is None:
            return {
                "ok": False,
                "failure_reason": failure_reason or "unknown",
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            }
        return {
            "ok": True,
            "identified": identified,
            "destination_hash": dest_hash.hex(),
            "aspect": aspect,
        }

    def _rns_link_identify(self, args: dict[str, Any]) -> dict[str, Any]:
        dest_hash, aspect = self._parse_rns_link_args(args)
        manager = self._require_rns_link_manager()
        ok, failure_reason = manager.identify(dest_hash, aspect)
        return {
            "ok": ok,
            "failure_reason": failure_reason,
            "destination_hash": dest_hash.hex(),
            "aspect": aspect,
        }

    def _rns_link_request(self, args: dict[str, Any]) -> dict[str, Any]:
        import base64

        dest_hash, aspect = self._parse_rns_link_args(args)
        path = args.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("path is required")
        manager = self._require_rns_link_manager()
        link, _identified, failure_reason = self._await_rns_link_coro(
            manager.open_link(dest_hash, aspect, auto_identify=False)
        )
        if link is None:
            return {
                "ok": False,
                "failure_reason": failure_reason or "unknown",
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            }

        data_b64 = args.get("data_b64")
        try:
            body_bytes = base64.b64decode(data_b64, validate=True) if data_b64 else None
        except Exception as exc:
            raise ValueError("invalid data_b64") from exc
        if body_bytes is None or len(body_bytes) == 0:
            link_request_data = None
        else:
            from RNS.vendor import umsgpack

            try:
                link_request_data = umsgpack.unpackb(body_bytes)
            except Exception as exc:
                raise ValueError(f"data_msgpack_decode_failed: {exc}") from exc

        timeout = args.get("timeout")
        done = threading.Event()
        result: dict[str, Any] = {
            "ok": False,
            "destination_hash": dest_hash.hex(),
            "aspect": aspect,
        }

        def on_response(request_receipt):
            raw = request_receipt.response
            from RNS.vendor import umsgpack

            try:
                if hasattr(raw, "read") and not isinstance(raw, (bytes, bytearray)):
                    raw_to_pack = raw.read()
                else:
                    raw_to_pack = raw
                result["body_b64"] = base64.b64encode(
                    umsgpack.packb(raw_to_pack)
                ).decode("ascii")
                result["ok"] = True
            except Exception as exc:
                result["failure_reason"] = f"response_encode_failed: {exc}"
            done.set()

        def on_failed(_receipt=None):
            result["failure_reason"] = "request_failed"
            done.set()

        def on_progress(_receipt):
            return

        try:
            manager.request(
                dest_hash,
                aspect,
                path,
                link_request_data,
                response_callback=on_response,
                failed_callback=on_failed,
                progress_callback=on_progress,
                timeout=timeout,
            )
        except Exception as exc:
            return {
                "ok": False,
                "failure_reason": f"request_dispatch_failed: {exc}",
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            }

        wait_timeout = float(timeout) if timeout is not None else 30.0
        if not done.wait(timeout=max(wait_timeout, 1.0) + 5.0):
            result["failure_reason"] = "request_timeout"
        return result

    def _rns_link_send(self, args: dict[str, Any]) -> dict[str, Any]:
        import base64

        dest_hash, aspect = self._parse_rns_link_args(args)
        manager = self._require_rns_link_manager()
        payload_b64 = args.get("payload_b64", "")
        try:
            payload = (
                base64.b64decode(payload_b64, validate=True) if payload_b64 else b""
            )
        except Exception as exc:
            raise ValueError("invalid payload_b64") from exc
        ok, failure_reason = manager.send_packet(dest_hash, aspect, payload)
        return {
            "ok": ok,
            "failure_reason": failure_reason,
            "destination_hash": dest_hash.hex(),
            "aspect": aspect,
        }

    def _rns_link_close(self, args: dict[str, Any]) -> dict[str, Any]:
        dest_hash, aspect = self._parse_rns_link_args(args)
        manager = self._require_rns_link_manager()
        ok = manager.close(dest_hash, aspect)
        return {
            "ok": ok,
            "failure_reason": None if ok else "no_active_link",
            "destination_hash": dest_hash.hex(),
            "aspect": aspect,
        }

    def on_rns_link_event(self, payload: dict[str, Any]) -> None:
        if not self._plugins_runtime_enabled():
            return
        event_payload = {
            "event": payload.get("event"),
            "destination_hash": payload.get("destination_hash"),
            "aspect": payload.get("aspect"),
            "payload_b64": payload.get("payload_b64"),
        }
        for record in list(self._plugins.values()):
            if record.enabled and self._hook_allowed(record, "rns.link.event"):
                self.dispatch_hook(record.id, "rns.link.event", event_payload)

    def _destination_path_read(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self.app or not getattr(self.app, "reticulum", None):
            return {"paths": [], "total": 0, "responsive": 0, "unresponsive": 0}
        search = args.get("search")
        limit = int(args.get("limit") or 200)
        handler = getattr(self.app, "rnpath_handler", None)
        if handler:
            result = handler.get_path_table(
                search=str(search).strip() if search else None,
                limit=limit,
            )
            paths = [
                {
                    "destination_hash": entry["hash"],
                    "hops": entry["hops"],
                    "via": entry.get("via"),
                    "interface": entry.get("interface"),
                    "state": entry.get("state"),
                    "timestamp": entry.get("timestamp"),
                }
                for entry in result.get("table", [])
            ]
            return {
                "paths": paths,
                "total": result.get("total", len(paths)),
                "responsive": result.get("responsive", 0),
                "unresponsive": result.get("unresponsive", 0),
            }
        destination_hash = args.get("destination_hash")
        paths: list[dict[str, Any]] = []
        reticulum = self.app.reticulum
        if destination_hash:
            hashes = [destination_hash]
        else:
            hashes = []
            try:
                table = reticulum.get_path_table()
                hashes = [
                    entry.get("destination_hash")
                    for entry in table
                    if entry.get("destination_hash")
                ]
            except Exception:
                hashes = []
        for item in hashes:
            if not item:
                continue
            try:
                raw = bytes.fromhex(item) if isinstance(item, str) else item
                hops = (
                    reticulum.get_hops_to(raw)
                    if hasattr(reticulum, "get_hops_to")
                    else None
                )
                paths.append({"destination_hash": item, "hops": hops})
            except Exception:
                paths.append({"destination_hash": item, "hops": None})
        return {
            "paths": paths,
            "total": len(paths),
            "responsive": 0,
            "unresponsive": 0,
        }

    def invoke(
        self, plugin_id: str, method: str, args: dict[str, Any] | None = None
    ) -> Any:
        self._require_runtime_enabled()
        record = self._require_plugin(plugin_id)
        if not record.enabled:
            raise PermissionError("plugin is disabled")
        args = args or {}
        try:
            if method == "callManager":
                capability = args.get("capability")
                if not isinstance(capability, str) or not capability:
                    raise ValueError("capability is required")
                return self.call_manager(plugin_id, capability, args.get("args") or {})
            if method == "readPaths":
                return self.call_manager(plugin_id, "destinationPath.read", args)
            backend = record.manifest.get("backend")
            if not backend:
                raise ValueError(f"unknown method: {method}")
            return self._invoke_wasm(record, method, args or {})
        except Exception as exc:
            self._record_plugin_failure(record, exc, auto_disable=True)
            raise

    def _resolve_backend_wasm_path(self, record: PluginRecord) -> str:
        backend = record.manifest["backend"]
        wasm_path = os.path.join(record.install_path, backend["entry"])
        if not os.path.isfile(wasm_path):
            return self._ensure_minimal_wasm(record)
        try:
            validate_wasm_file(wasm_path)
            with open(wasm_path, "rb") as handle:
                if handle.read(4) != b"\x00asm":
                    raise PluginSecurityError("invalid wasm module")
        except (PluginSecurityError, OSError, ValueError):
            parent = os.path.dirname(wasm_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if os.path.isfile(wasm_path):
                os.remove(wasm_path)
            return self._ensure_minimal_wasm(record)
        return wasm_path

    def _invoke_wasm(
        self, record: PluginRecord, method: str, args: dict[str, Any]
    ) -> Any:
        wasmtime = self._load_wasmtime()
        wasm_path = self._resolve_backend_wasm_path(record)
        engine = wasmtime.Engine()
        module = wasmtime.Module.from_file(engine, wasm_path)
        store = wasmtime.Store(engine)
        store.set_fuel(1_000_000)
        linker = wasmtime.Linker(engine)
        logs: list[str] = []

        def host_log(caller, ptr, length) -> None:
            memory = caller.get("memory")
            if memory is None:
                return
            data = memory.read(store, ptr, ptr + length)
            logs.append(data.decode("utf-8", errors="replace"))

        linker.define_func(
            "host",
            "log",
            wasmtime.FuncType([wasmtime.ValType.i32(), wasmtime.ValType.i32()], []),
            host_log,
        )
        instance = linker.instantiate(store, module)
        payload = json.dumps({"method": method, "args": args}).encode("utf-8")
        validate_invoke_payload(payload)
        exports = cast(Any, instance.exports(store))
        memory = exports["memory"]
        alloc = exports.get("alloc")
        if alloc:
            ptr = alloc(store, len(payload))
        else:
            ptr = 0
            if memory.data_len(store) < len(payload):
                memory.grow(
                    store,
                    max(1, (len(payload) - memory.data_len(store) + 65535) // 65536),
                )
            data = memory.data_ptr(store)
            data[ptr : ptr + len(payload)] = payload
        invoke = exports["invoke"]
        invoke(store, ptr, len(payload), 0)
        return {"ok": True, "logs": logs}

    def _ensure_minimal_wasm(self, record: PluginRecord) -> str:
        wasmtime = self._load_wasmtime()
        wasm_bytes = wasmtime.wat2wasm(MINIMAL_PLUGIN_WAT)
        backend = record.manifest["backend"]
        wasm_path = os.path.join(record.install_path, backend["entry"])
        os.makedirs(os.path.dirname(wasm_path), exist_ok=True)
        with open(wasm_path, "wb") as handle:
            handle.write(wasm_bytes)
        return wasm_path

    def dispatch_hook(self, plugin_id: str, hook: str, payload: dict[str, Any]) -> None:
        record = self._plugins.get(plugin_id)
        if not record or not record.enabled:
            return
        if not self._hook_allowed(record, hook):
            return
        try:
            if record.manifest.get("backend"):
                self._invoke_wasm(record, "on_hook", {"hook": hook, "payload": payload})
            self._broadcast_plugin_event(plugin_id, hook, payload)
        except Exception as exc:
            self._record_plugin_failure(record, exc, auto_disable=True)

    def _validate_plugin_runtime(self, record: PluginRecord) -> None:
        manifest = record.manifest
        frontend = manifest.get("frontend")
        if frontend:
            entry = frontend.get("entry")
            if not isinstance(entry, str) or not entry.strip():
                raise ValueError("plugin frontend entry is missing")
            frontend_path = self.asset_path(record.id, entry)
            if os.path.getsize(frontend_path) <= 0:
                raise ValueError("plugin frontend entry is empty")
        backend = manifest.get("backend")
        if not backend:
            return
        entry = backend.get("entry")
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("plugin backend entry is missing")
        wasm_path = self._resolve_backend_wasm_path(record)
        wasmtime = self._load_wasmtime()
        engine = wasmtime.Engine()
        try:
            wasmtime.Module.from_file(engine, wasm_path)
        except Exception as exc:
            raise ValueError(f"invalid backend wasm module: {exc}") from exc

    def _record_plugin_failure(
        self,
        record: PluginRecord,
        exc: Exception | str,
        *,
        auto_disable: bool,
    ) -> dict[str, Any] | None:
        should_disable = False
        disable_reason = str(exc)
        with self._lock:
            now = time.time()
            if now - record.last_error_at > PLUGIN_ERROR_WINDOW_SECONDS:
                record.error_count = 0
            record.error_count += 1
            record.last_error_at = now
            if auto_disable and record.error_count >= PLUGIN_ERROR_BUDGET:
                should_disable = True
                disable_reason = (
                    f"Auto-disabled after {record.error_count} errors: {disable_reason}"
                )
        if should_disable:
            return self.disable(record.id, reason=disable_reason)
        return None

    def on_announce_received(
        self,
        aspect: str,
        destination_hash: bytes,
        announced_identity: Any,
        app_data: bytes,
        announce_packet_hash: bytes,
    ) -> None:
        if not self._plugins_runtime_enabled():
            return
        payload = {
            "aspect": aspect,
            "destination_hash": destination_hash.hex()
            if isinstance(destination_hash, bytes)
            else str(destination_hash),
            "app_data": app_data.decode("utf-8", errors="replace")
            if isinstance(app_data, bytes)
            else str(app_data),
            "announce_packet_hash": announce_packet_hash.hex()
            if isinstance(announce_packet_hash, bytes)
            else str(announce_packet_hash),
        }
        for record in list(self._plugins.values()):
            if record.enabled and self._hook_allowed(record, "announce.received"):
                self.dispatch_hook(record.id, "announce.received", payload)

    def _register_plugin_hooks(self, record: PluginRecord) -> None:
        if not self.app:
            return
        hooks = (record.manifest.get("permissions") or {}).get("hooks") or []
        if "announce.received" in hooks and not getattr(
            self.app, "_plugin_announce_handler_registered", False
        ):
            from meshchatx.src.backend.announce_handler import AnnounceHandler
            import RNS

            handler = AnnounceHandler(
                "meshchatx.plugin",
                lambda aspect, dh, ai, ad, aph: self.on_announce_received(
                    aspect, dh, ai, ad, aph
                ),
            )
            RNS.Transport.register_announce_handler(handler)
            self.app._plugin_announce_handler_registered = True
            self.app._plugin_announce_handler = handler

    def _unregister_plugin_hooks(self, record: PluginRecord) -> None:
        if not self.app:
            return
        any_enabled_hooks = any(
            record.enabled
            and "announce.received"
            in ((p.manifest.get("permissions") or {}).get("hooks") or [])
            for p in self._plugins.values()
        )
        if any_enabled_hooks:
            return
        handler = getattr(self.app, "_plugin_announce_handler", None)
        if not handler:
            return
        try:
            import RNS

            if handler in RNS.Transport.announce_handlers:
                RNS.Transport.announce_handlers.remove(handler)
            self.app._plugin_announce_handler_registered = False
            self.app._plugin_announce_handler = None
        except Exception:
            pass

    def _broadcast_plugin_event(
        self, plugin_id: str, event: str, payload: dict[str, Any]
    ) -> None:
        if not self.app:
            return
        from meshchatx.src.backend.async_utils import AsyncUtils
        import json as json_module

        message = json_module.dumps(
            {
                "type": "plugin.event",
                "plugin_id": plugin_id,
                "event": event,
                "payload": payload,
            }
        )
        AsyncUtils.run_async(self.app.websocket_broadcast(message))

    def install_bundled_examples(self) -> None:
        if not self._plugins_runtime_enabled():
            return
        bundled_root = os.path.join(os.path.dirname(__file__), "data", "plugins")
        if not os.path.isdir(bundled_root):
            return
        for name in sorted(os.listdir(bundled_root)):
            source = os.path.join(bundled_root, name)
            if not os.path.isdir(source):
                continue
            manifest_path = os.path.join(source, "plugin.json")
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            if manifest.get("id") not in self._plugins:
                self.install_from_directory(source)
