# SPDX-License-Identifier: 0BSD

"""Identity-scoped wrapper around vendored rns_filesync.FileSyncService."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from collections.abc import Callable
from typing import Any

from rns_filesync.constants import ANNOUNCE_INTERVAL_DEFAULT
from rns_filesync.paths import PathJailError, normalize_relpath, relative_to_root
from rns_filesync.permissions import PermissionStore
from rns_filesync.service import FileSyncService

_ALL_ALIASES = frozenset({"all", "a", "everyone", "*"})

# Cap for in-app sync-tree uploads (local control plane only).
MANAGER_UPLOAD_MAX_BYTES = 64 * 1024 * 1024


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


def _is_forbidden_entry_name(name: str) -> bool:
    """Reject hidden and protocol sidecar names in the file manager."""
    cleaned = str(name or "")
    if not cleaned or cleaned in (".", ".."):
        return True
    if cleaned.startswith("."):
        return True
    if cleaned == ".rns-filesync.db" or cleaned.startswith(".rns-filesync"):
        return True
    if cleaned.startswith(".rns-xfer"):
        return True
    if cleaned in {"identity", "identity.bak"}:
        return True
    return False


def _sanitize_upload_basename(filename: str | None) -> str | None:
    """Keep only a safe basename for uploads. Fail closed on escape tricks."""
    raw = str(filename or "").strip()
    if not raw or "\x00" in raw:
        return None
    base = os.path.basename(raw.replace("\\", "/"))
    if not base or base in (".", "..") or _is_forbidden_entry_name(base):
        return None
    if "/" in base or "\\" in base:
        return None
    return base


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
        "ssl",
        "page_nodes",
        "map_overlays",
        "reticulum-docs",
        "meshchatx-docs",
        "repository-server",
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

    def _sync_root(self) -> str:
        """Real path of the configured sync directory (file manager jail base)."""
        os.makedirs(self._sync_directory, exist_ok=True)
        return os.path.realpath(self._sync_directory)

    def _is_under_sync_root(self, candidate: str) -> bool:
        root = self._sync_root()
        real = os.path.realpath(candidate)
        return real == root or real.startswith(root + os.sep)

    def _resolve_manager_path(
        self,
        path: str | None,
        *,
        allow_root: bool = False,
        must_exist: bool = False,
    ) -> tuple[str | None, str | None]:
        """Resolve a path for the sync-root file manager.

        Returns (abspath, error). Fail closed with a generic error string.
        Empty path with allow_root returns the sync root itself.
        """
        root = self._sync_root()
        cleaned = str(path or "").strip()
        if not cleaned:
            if allow_root:
                return root, None
            return None, "path is required"

        # Absolute client paths are never accepted for the manager.
        if "\x00" in cleaned:
            return None, "path not allowed"
        if os.path.isabs(cleaned) or cleaned.startswith(("/", "\\")):
            return None, "path not allowed"
        if len(cleaned) >= 2 and cleaned[1] == ":":
            return None, "path not allowed"

        try:
            safe_rel = normalize_relpath(cleaned)
        except PathJailError:
            return None, "path not allowed"

        parts = safe_rel.replace("\\", "/").split("/")
        if any(_is_forbidden_entry_name(part) for part in parts):
            return None, "path not allowed"

        joined = os.path.join(root, safe_rel)
        # Reject symlink parents that escape before realpath of missing leaves.
        parent = os.path.dirname(joined)
        if parent != root and not self._is_under_sync_root(parent):
            return None, "path not allowed"
        if os.path.lexists(joined) and os.path.islink(joined):
            real = os.path.realpath(joined)
            if real != root and not real.startswith(root + os.sep):
                return None, "path not allowed"
            if must_exist and not os.path.exists(real):
                return None, "path not found"
            return real, None

        if must_exist and not os.path.lexists(joined):
            return None, "path not found"

        try:
            real = os.path.realpath(joined)
        except OSError:
            return None, "path not allowed"

        if real != root and not real.startswith(root + os.sep):
            return None, "path not allowed"
        if not allow_root and real == root:
            return None, "path not allowed"
        return real, None

    def _relpath_under_sync(self, abspath: str) -> str | None:
        try:
            return relative_to_root(self._sync_root(), abspath)
        except PathJailError:
            return None

    def _nudge_inventory(self, relpath: str | None = None) -> None:
        if self.service is None:
            return
        inventory = getattr(self.service, "inventory", None)
        if inventory is None:
            return
        with contextlib.suppress(Exception):
            if relpath:
                inventory.update_from_path(relpath)
            else:
                inventory.scan()

    def list_tree(self, path: str | None = None) -> dict[str, Any]:
        """List files and directories under a relative path inside the sync root."""
        with self._lock:
            target, err = self._resolve_manager_path(path, allow_root=True)
            if err or target is None:
                return {"ok": False, "error": err or "path not allowed"}
            if not os.path.isdir(target):
                return {"ok": False, "error": "not a directory"}

            root = self._sync_root()
            entries: list[dict[str, Any]] = []
            try:
                names = sorted(os.listdir(target), key=str.lower)
            except OSError as exc:
                return {"ok": False, "error": str(exc)}

            for name in names:
                if _is_forbidden_entry_name(name):
                    continue
                full = os.path.join(target, name)
                if os.path.islink(full):
                    real = os.path.realpath(full)
                    if real != root and not real.startswith(root + os.sep):
                        continue
                else:
                    real = os.path.realpath(full)
                    if real != root and not real.startswith(root + os.sep):
                        continue

                is_dir = os.path.isdir(real) and not os.path.islink(full)
                # Treat in-jail symlinks to dirs as dirs for navigation only when target stays inside.
                if os.path.islink(full) and os.path.isdir(real):
                    is_dir = True
                rel = self._relpath_under_sync(real)
                if rel is None and real == root:
                    continue
                if rel is None:
                    continue
                item: dict[str, Any] = {
                    "name": name,
                    "path": rel,
                    "type": "dir" if is_dir else "file",
                }
                if not is_dir:
                    try:
                        item["size"] = os.path.getsize(real)
                    except OSError:
                        item["size"] = 0
                entries.append(item)

            current_rel = ""
            if target != root:
                current_rel = self._relpath_under_sync(target) or ""
            parent_rel = None
            if target != root:
                parent_abs = os.path.dirname(target)
                if parent_abs == root:
                    parent_rel = ""
                else:
                    parent_rel = self._relpath_under_sync(parent_abs)

            return {
                "ok": True,
                "root": root,
                "current": current_rel,
                "parent": parent_rel,
                "entries": entries,
            }

    def manager_mkdir(self, path: str) -> dict[str, Any]:
        """Create a directory under the sync root (relative path)."""
        with self._lock:
            cleaned = str(path or "").strip()
            if not cleaned:
                return {"ok": False, "error": "path is required"}
            # Resolve parent and create leaf so we do not require the leaf to exist.
            try:
                safe_rel = normalize_relpath(cleaned)
            except PathJailError:
                return {"ok": False, "error": "path not allowed"}
            parts = safe_rel.replace("\\", "/").split("/")
            if any(_is_forbidden_entry_name(part) for part in parts):
                return {"ok": False, "error": "path not allowed"}
            leaf = parts[-1]
            parent_rel = "/".join(parts[:-1]) if len(parts) > 1 else ""
            parent_abs, err = self._resolve_manager_path(
                parent_rel if parent_rel else None,
                allow_root=True,
                must_exist=True,
            )
            if err or parent_abs is None:
                return {"ok": False, "error": err or "path not allowed"}
            if not os.path.isdir(parent_abs):
                return {"ok": False, "error": "parent is not a directory"}
            if os.path.islink(parent_abs):
                return {"ok": False, "error": "path not allowed"}

            new_path = os.path.join(parent_abs, leaf)
            if not self._is_under_sync_root(os.path.dirname(new_path)):
                return {"ok": False, "error": "path not allowed"}
            if os.path.lexists(new_path):
                return {"ok": False, "error": "already exists"}
            try:
                os.mkdir(new_path)
            except OSError as exc:
                return {"ok": False, "error": str(exc)}
            real = os.path.realpath(new_path)
            if not self._is_under_sync_root(real):
                with contextlib.suppress(OSError):
                    os.rmdir(new_path)
                return {"ok": False, "error": "path not allowed"}
            rel = self._relpath_under_sync(real) or safe_rel
            return {"ok": True, "path": rel}

    def manager_upload(
        self,
        *,
        filename: str | None,
        data: bytes,
        subdir: str | None = None,
    ) -> dict[str, Any]:
        """Write an uploaded file under the sync root."""
        with self._lock:
            if not isinstance(data, (bytes, bytearray)):
                return {"ok": False, "error": "invalid upload data"}
            if len(data) > MANAGER_UPLOAD_MAX_BYTES:
                return {"ok": False, "error": "upload too large"}
            base = _sanitize_upload_basename(filename)
            if base is None:
                return {"ok": False, "error": "invalid filename"}

            parent_abs, err = self._resolve_manager_path(
                subdir,
                allow_root=True,
                must_exist=True,
            )
            if err or parent_abs is None:
                return {"ok": False, "error": err or "path not allowed"}
            if not os.path.isdir(parent_abs) or os.path.islink(parent_abs):
                return {"ok": False, "error": "path not allowed"}

            dest = os.path.join(parent_abs, base)
            if os.path.islink(dest):
                return {"ok": False, "error": "path not allowed"}
            if os.path.lexists(dest):
                real_existing = os.path.realpath(dest)
                if not self._is_under_sync_root(real_existing):
                    return {"ok": False, "error": "path not allowed"}

            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    prefix=".upload-",
                    suffix=".tmp",
                    dir=parent_abs,
                )
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(data)
                except Exception:
                    with contextlib.suppress(OSError):
                        os.close(fd)
                    raise
                if not self._is_under_sync_root(tmp_path):
                    with contextlib.suppress(OSError):
                        os.unlink(tmp_path)
                    return {"ok": False, "error": "path not allowed"}
                os.replace(tmp_path, dest)
                tmp_path = None
            except OSError as exc:
                if tmp_path:
                    with contextlib.suppress(OSError):
                        os.unlink(tmp_path)
                return {"ok": False, "error": str(exc)}

            real = os.path.realpath(dest)
            if not self._is_under_sync_root(real) or not os.path.isfile(real):
                with contextlib.suppress(OSError):
                    os.unlink(dest)
                return {"ok": False, "error": "path not allowed"}
            rel = self._relpath_under_sync(real)
            if rel is None:
                with contextlib.suppress(OSError):
                    os.unlink(dest)
                return {"ok": False, "error": "path not allowed"}
            self._nudge_inventory(rel)
            return {"ok": True, "path": rel, "size": len(data)}

    def manager_delete(self, path: str) -> dict[str, Any]:
        """Delete a file or empty directory under the sync root."""
        with self._lock:
            root = self._sync_root()
            try:
                safe_rel = normalize_relpath(str(path or "").strip())
            except PathJailError:
                return {"ok": False, "error": "path not allowed"}
            lex_path = os.path.join(root, safe_rel)
            if os.path.islink(lex_path):
                return {"ok": False, "error": "path not allowed"}

            target, err = self._resolve_manager_path(
                path,
                allow_root=False,
                must_exist=True,
            )
            if err or target is None:
                return {"ok": False, "error": err or "path not allowed"}
            if target == root:
                return {"ok": False, "error": "path not allowed"}

            rel = self._relpath_under_sync(target)
            if rel is None:
                return {"ok": False, "error": "path not allowed"}

            try:
                if os.path.isdir(target):
                    try:
                        os.rmdir(target)
                    except OSError:
                        return {"ok": False, "error": "directory is not empty"}
                elif os.path.isfile(target):
                    os.unlink(target)
                else:
                    return {"ok": False, "error": "path not found"}
            except OSError as exc:
                return {"ok": False, "error": str(exc)}

            self._nudge_inventory(rel)
            return {"ok": True, "path": rel}

    def manager_content(self, path: str) -> dict[str, Any]:
        """Resolve a file under the sync root for download streaming."""
        with self._lock:
            root = self._sync_root()
            try:
                safe_rel = normalize_relpath(str(path or "").strip())
            except PathJailError:
                return {"ok": False, "error": "path not allowed"}
            lex_path = os.path.join(root, safe_rel)
            if os.path.islink(lex_path):
                return {"ok": False, "error": "path not allowed"}

            target, err = self._resolve_manager_path(
                path,
                allow_root=False,
                must_exist=True,
            )
            if err or target is None:
                return {"ok": False, "error": err or "path not allowed"}
            if not os.path.isfile(target):
                return {"ok": False, "error": "not a file"}
            rel = self._relpath_under_sync(target)
            if rel is None:
                return {"ok": False, "error": "path not allowed"}
            return {
                "ok": True,
                "abspath": target,
                "path": rel,
                "filename": os.path.basename(target),
                "size": os.path.getsize(target),
            }

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
