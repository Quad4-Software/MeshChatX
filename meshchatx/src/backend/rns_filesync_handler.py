# SPDX-License-Identifier: 0BSD

"""Identity-scoped wrapper around vendored rns_filesync.FileSyncService."""

from __future__ import annotations

import contextlib
import json
import os
import threading
from collections.abc import Callable
from typing import Any

from rns_filesync.constants import ANNOUNCE_INTERVAL_DEFAULT
from rns_filesync.paths import PathJailError, normalize_relpath
from rns_filesync.permissions import PermissionStore
from rns_filesync.service import FileSyncService

_ALL_ALIASES = frozenset({"all", "a", "everyone", "*"})


def _normalize_peer_hash(value: str | None) -> str | None:
    cleaned = str(value or "").strip().lower().replace(":", "")
    if not cleaned:
        return None
    if cleaned in _ALL_ALIASES:
        return "all"
    if len(cleaned) != 32:
        return None
    try:
        bytes.fromhex(cleaned)
    except ValueError:
        return None
    return cleaned


_RESERVED_SYNC_TOP = frozenset(
    {
        "identity",
        "identity.bak",
        "bots",
        "plugins",
        "lxmf",
        "lxmf_router",
        "telephone",
        "rrc_history",
        "rrc_server",
        "rncp_received",
        "rncp_shared",
        "rncp",
        "database-backups",
        "snapshots",
        "database.db",
    },
)


class RnsFilesyncHandler:
    """Host FileSync against the shared Reticulum stack for one identity."""

    def __init__(
        self,
        reticulum_instance,
        identity,
        storage_dir: str,
        emit_callback: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.reticulum = reticulum_instance
        self.identity = identity
        self.storage_dir = os.path.realpath(storage_dir)
        self._emit_callback = emit_callback
        self._lock = threading.RLock()
        self.service: FileSyncService | None = None
        self._permissions_cache: PermissionStore | None = None

        self._root = os.path.join(self.storage_dir, "filesync")
        self._settings_path = os.path.join(self._root, "settings.json")
        self._acl_path = os.path.join(self._root, "acl.txt")
        self._sync_directory = os.path.join(self._root, "sync")
        self._monitor = True
        self._announce_interval = ANNOUNCE_INTERVAL_DEFAULT
        self._load_settings()
        os.makedirs(self._root, exist_ok=True)
        os.makedirs(self._sync_directory, exist_ok=True)

    def _emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if not self._emit_callback:
            return
        message = {"type": event_type}
        if payload:
            message.update(payload)
        try:
            self._emit_callback(message)
        except Exception:
            pass

    def _resolve_sync_directory(self, path: str) -> str | None:
        cleaned = str(path or "").strip()
        if not cleaned:
            return None
        resolved = os.path.realpath(os.path.expanduser(cleaned))
        root = self.storage_dir
        # Never sync the whole identity tree (would expose keys / DB).
        if resolved == root:
            return None
        if not resolved.startswith(root + os.sep):
            return None
        rel = os.path.relpath(resolved, root)
        first = rel.split(os.sep, 1)[0]
        if first in _RESERVED_SYNC_TOP or first.endswith(".db"):
            return None
        return resolved

    def _load_settings(self) -> None:
        os.makedirs(self._root, exist_ok=True)
        if not os.path.isfile(self._settings_path):
            return
        try:
            with open(self._settings_path, encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        sync_dir = data.get("sync_directory")
        if isinstance(sync_dir, str) and sync_dir.strip():
            resolved = self._resolve_sync_directory(sync_dir)
            if resolved is not None:
                self._sync_directory = resolved
        monitor = data.get("monitor")
        if isinstance(monitor, bool):
            self._monitor = monitor
        interval = data.get("announce_interval")
        if isinstance(interval, int) and interval >= 10:
            self._announce_interval = interval

    def _save_settings(self) -> None:
        os.makedirs(self._root, exist_ok=True)
        payload = {
            "sync_directory": self._sync_directory,
            "monitor": self._monitor,
            "announce_interval": self._announce_interval,
        }
        tmp = f"{self._settings_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, self._settings_path)

    def _load_permissions(self) -> PermissionStore:
        permissions = PermissionStore()
        enforce_override: bool | None = None
        if os.path.isfile(self._acl_path):
            try:
                with open(self._acl_path, encoding="utf-8") as handle:
                    text = handle.read()
                lines = text.splitlines()
                if lines:
                    first = lines[0].strip()
                    if first == "# enforce=false":
                        enforce_override = False
                    elif first == "# enforce=true":
                        enforce_override = True
                permissions.load_allowed_text(text)
                if enforce_override is not None:
                    permissions._enforce = enforce_override
            except Exception:
                pass
        return permissions

    def _save_acl(self, permissions: PermissionStore) -> None:
        os.makedirs(self._root, exist_ok=True)
        lines: list[str] = []
        rules = permissions.as_dict()
        for perm in ("read", "write", "delete"):
            for target in rules.get(perm, []):
                short = {"read": "r", "write": "w", "delete": "d"}[perm]
                lines.append(f"{short}:{target}")
        if permissions.enabled:
            lines.insert(0, "# enforce=true")
        else:
            lines.insert(0, "# enforce=false")
        tmp = f"{self._acl_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.replace(tmp, self._acl_path)
        self._permissions_cache = permissions

    def _wire_callbacks(self, service: FileSyncService) -> None:
        service.on_peer_connected = lambda payload: self._emit(
            "filesync.peer.connected",
            payload if isinstance(payload, dict) else {"peer": payload},
        )
        service.on_peer_disconnected = lambda payload: self._emit(
            "filesync.peer.disconnected",
            payload if isinstance(payload, dict) else {"peer": payload},
        )
        service.on_sync_progress = lambda payload: self._emit(
            "filesync.sync.progress",
            payload if isinstance(payload, dict) else {"progress": payload},
        )
        service.on_file_updated = lambda payload: self._emit(
            "filesync.file.updated",
            payload if isinstance(payload, dict) else {"path": payload},
        )
        service.on_file_deleted = lambda payload: self._emit(
            "filesync.file.deleted",
            payload if isinstance(payload, dict) else {"path": payload},
        )
        service.on_error = lambda payload: self._emit(
            "filesync.error",
            payload if isinstance(payload, dict) else {"error": str(payload)},
        )

    def _permissions(self) -> PermissionStore:
        if self.service is not None:
            return self.service.permissions
        if self._permissions_cache is not None:
            return self._permissions_cache
        self._permissions_cache = self._load_permissions()
        return self._permissions_cache

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            if self.service is not None and self.service.get_status().get("running"):
                status = self.service.get_status()
                status["monitor"] = self._monitor
                status["announce_interval"] = self._announce_interval
                status["config_directory"] = self._root
                status["storage_directory"] = self.storage_dir
                return status
            return {
                "running": False,
                "sync_directory": self._sync_directory,
                "identity_hash": (
                    self.identity.hash.hex()
                    if getattr(self.identity, "hash", None) is not None
                    else None
                ),
                "destination_hash": None,
                "peers": 0,
                "files": 0,
                "whitelist": self._permissions().enabled,
                "monitor": self._monitor,
                "announce_interval": self._announce_interval,
                "config_directory": self._root,
                "storage_directory": self.storage_dir,
            }

    def list_directories(self, path: str | None = None) -> dict[str, Any]:
        """List subdirectories under identity storage for the folder browser."""
        with self._lock:
            root = self.storage_dir
            cleaned = str(path or "").strip()
            if cleaned:
                target = self._resolve_sync_directory(cleaned)
                if target is None:
                    return {
                        "ok": False,
                        "error": "path must stay under identity storage",
                    }
            else:
                os.makedirs(self._root, exist_ok=True)
                target = self._root

            if not os.path.isdir(target):
                # Default sync path can appear in status before the folder exists.
                # Walk up to the nearest existing directory still inside the jail.
                cursor = target
                while True:
                    parent = os.path.dirname(cursor)
                    if parent == cursor:
                        break
                    if parent != root and not parent.startswith(root + os.sep):
                        break
                    cursor = parent
                    if os.path.isdir(cursor):
                        target = cursor
                        break
                if not os.path.isdir(target):
                    os.makedirs(self._root, exist_ok=True)
                    target = self._root

            entries: list[dict[str, str]] = []
            try:
                for name in sorted(os.listdir(target), key=str.lower):
                    if name.startswith("."):
                        continue
                    full = os.path.join(target, name)
                    if not os.path.isdir(full):
                        continue
                    resolved = os.path.realpath(full)
                    if resolved != root and not resolved.startswith(root + os.sep):
                        continue
                    entries.append({"name": name, "path": resolved})
            except OSError as exc:
                return {"ok": False, "error": str(exc)}

            current = os.path.realpath(target)
            parent = None
            if current != root:
                candidate = os.path.dirname(current)
                if candidate == root or candidate.startswith(root + os.sep):
                    parent = candidate

            return {
                "ok": True,
                "root": root,
                "current": current,
                "parent": parent,
                "directories": entries,
            }

    def create_directory(self, parent: str | None, name: str) -> dict[str, Any]:
        """Create a subdirectory under identity storage for sync folders."""
        with self._lock:
            cleaned_name = str(name or "").strip()
            if (
                not cleaned_name
                or cleaned_name in (".", "..")
                or "/" in cleaned_name
                or "\\" in cleaned_name
                or cleaned_name.startswith(".")
            ):
                return {"ok": False, "error": "invalid directory name"}

            parent_cleaned = str(parent or "").strip()
            if parent_cleaned:
                parent_resolved = self._resolve_sync_directory(parent_cleaned)
            else:
                os.makedirs(self._root, exist_ok=True)
                parent_resolved = self._root
            if parent_resolved is None:
                return {
                    "ok": False,
                    "error": "parent must stay under identity storage",
                }

            new_path = os.path.join(parent_resolved, cleaned_name)
            resolved = self._resolve_sync_directory(new_path)
            if resolved is None:
                return {
                    "ok": False,
                    "error": "path must stay under identity storage",
                }
            try:
                os.makedirs(resolved, exist_ok=False)
            except FileExistsError:
                return {"ok": False, "error": "directory already exists"}
            except OSError as exc:
                return {"ok": False, "error": str(exc)}
            return {"ok": True, "path": resolved}

    def start(
        self,
        *,
        sync_directory: str | None = None,
        monitor: bool | None = None,
        announce_interval: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if sync_directory is not None:
                resolved = self._resolve_sync_directory(sync_directory)
                if resolved is None:
                    return {
                        "ok": False,
                        "error": "sync_directory must stay under identity storage",
                    }
                self._sync_directory = resolved
            if monitor is not None:
                self._monitor = bool(monitor)
            if announce_interval is not None:
                try:
                    interval = int(announce_interval)
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid announce_interval"}
                if interval < 10:
                    return {"ok": False, "error": "announce_interval must be >= 10"}
                self._announce_interval = interval

            if self.service is not None:
                status = self.service.get_status()
                if status.get("running"):
                    return {"ok": True, "already_running": True, **status}

            os.makedirs(self._sync_directory, exist_ok=True)
            permissions = self._load_permissions()
            self._permissions_cache = permissions

            service = FileSyncService(
                identity=self.identity,
                sync_directory=self._sync_directory,
                storage_dir=self._root,
                reticulum=self.reticulum,
                permissions=permissions,
                own_reticulum=False,
            )
            self._wire_callbacks(service)
            dest = service.start(
                monitor=self._monitor,
                announce_interval=self._announce_interval,
            )
            self.service = service
            self._save_settings()
            status = service.get_status()
            return {
                "ok": True,
                "destination_hash": dest,
                **status,
            }

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return {"ok": True, "running": False}
            with contextlib.suppress(Exception):
                self.service.stop()
            self.service = None
            return {"ok": True, "running": False}

    def teardown(self) -> None:
        self.stop()
        self._permissions_cache = None

    def list_peers(self) -> list[dict[str, Any]]:
        with self._lock:
            if self.service is None:
                return []
            return self.service.list_peers()

    def list_files(self) -> list[dict[str, Any]]:
        with self._lock:
            if self.service is None:
                return []
            return self.service.list_files()

    def connect_peer(self, identity_hash: str) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return {"ok": False, "error": "filesync is not running"}
            cleaned = _normalize_peer_hash(identity_hash)
            if cleaned is None or cleaned == "all":
                return {"ok": False, "error": "invalid identity_hash"}
            return self.service.connect_peer(cleaned)

    def disconnect_peer(self, peer_id: str) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return {"ok": False, "error": "filesync is not running"}
            cleaned = str(peer_id or "").strip()
            if not cleaned:
                return {"ok": False, "error": "peer_id is required"}
            self.service.disconnect_peer(cleaned)
            return {"ok": True, "peer_id": cleaned}

    def announce_now(self) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return {"ok": False, "error": "filesync is not running"}
            self.service.announce_now()
            return {"ok": True}

    def browse_peer(self, peer_id: str, timeout: float = 10.0) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return {"ok": False, "error": "filesync is not running", "files": []}
            cleaned = str(peer_id or "").strip()
            if not cleaned:
                return {"ok": False, "error": "peer_id is required", "files": []}
            try:
                timeout_f = float(timeout)
            except (TypeError, ValueError):
                timeout_f = 10.0
            if timeout_f < 0.1:
                timeout_f = 0.1
            if timeout_f > 120.0:
                timeout_f = 120.0
            files = self.service.browse_peer(cleaned, timeout=timeout_f)
            return {"ok": True, "peer_id": cleaned, "files": files}

    def download_file(self, peer_id: str, path: str) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return {"ok": False, "error": "filesync is not running"}
            cleaned_peer = str(peer_id or "").strip()
            cleaned_path = str(path or "").strip()
            if not cleaned_peer:
                return {"ok": False, "error": "peer_id is required"}
            if not cleaned_path:
                return {"ok": False, "error": "path is required"}
            try:
                safe_path = normalize_relpath(cleaned_path)
            except PathJailError as exc:
                return {"ok": False, "error": str(exc)}
            return self.service.download_file(cleaned_peer, safe_path)

    def get_acl(self) -> dict[str, Any]:
        with self._lock:
            permissions = self._permissions()
            return {
                "enforce": permissions.enabled,
                "rules": permissions.as_dict(),
            }

    def update_acl(
        self,
        *,
        identity_hash: str | None = None,
        perms: list[str] | None = None,
        enforce: bool | None = None,
        rules_text: str | None = None,
        replace: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            if replace or rules_text is not None:
                permissions = PermissionStore()
                if rules_text:
                    permissions.load_allowed_text(rules_text)
            else:
                permissions = self._permissions()

            if identity_hash is not None and perms is not None:
                peer = _normalize_peer_hash(identity_hash)
                if peer is None:
                    return {"ok": False, "error": "invalid identity_hash"}
                granted = permissions.grant(peer, perms)
                if not granted and perms:
                    return {"ok": False, "error": "no valid permissions provided"}

            if enforce is not None:
                permissions._enforce = bool(enforce)

            if self.service is not None:
                self.service.permissions = permissions

            self._save_acl(permissions)
            return {
                "ok": True,
                "enforce": permissions.enabled,
                "rules": permissions.as_dict(),
            }

    def update_settings(
        self,
        *,
        sync_directory: str | None = None,
        monitor: bool | None = None,
        announce_interval: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            running = False
            if self.service is not None:
                running = bool(self.service.get_status().get("running"))

            if sync_directory is not None:
                if running:
                    return {
                        "ok": False,
                        "error": "stop filesync before changing sync directory",
                    }
                resolved = self._resolve_sync_directory(sync_directory)
                if resolved is None:
                    return {
                        "ok": False,
                        "error": "sync_directory must stay under identity storage",
                    }
                self._sync_directory = resolved

            if monitor is not None:
                self._monitor = bool(monitor)

            if announce_interval is not None:
                try:
                    interval = int(announce_interval)
                except (TypeError, ValueError):
                    return {"ok": False, "error": "invalid announce_interval"}
                if interval < 10:
                    return {"ok": False, "error": "announce_interval must be >= 10"}
                self._announce_interval = interval

            self._save_settings()
            return {
                "ok": True,
                "sync_directory": self._sync_directory,
                "monitor": self._monitor,
                "announce_interval": self._announce_interval,
                "running": running,
            }
