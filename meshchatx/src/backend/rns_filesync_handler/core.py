# SPDX-License-Identifier: 0BSD

"""Identity-scoped wrapper around vendored rns_filesync.FileSyncService."""

from __future__ import annotations

import contextlib
import os
import tempfile
import threading
from collections.abc import Callable
from typing import Any

from rns_filesync.constants import ANNOUNCE_INTERVAL_DEFAULT
from rns_filesync.permissions import PermissionStore
from rns_filesync.service import FileSyncService

from meshchatx.src.backend.results import err_result, err_result_from, ok_result
from meshchatx.src.json_store import load_json, save_json
from meshchatx.src.path_utils import (
    PathJailError,
    _fsync_dir,
    atomic_write_bytes,
    atomic_write_text,
    is_under_root,
    normalize_relpath,
    relative_to_root,
    resolve_under_root,
    safe_basename,
)

_ALL_ALIASES = frozenset({"all", "a", "everyone", "*"})

# Mirrors the reserved sidecar rules baked into vendored
# rns_filesync.paths.normalize_relpath so both implementations agree.
_SYNC_RESERVED_NAMES = frozenset({".rns-filesync.db"})
_SYNC_RESERVED_PREFIXES = (".rns-xfer-",)


def _normalize_sync_relpath(relpath: str) -> str:
    return normalize_relpath(
        relpath,
        reserved_names=_SYNC_RESERVED_NAMES,
        reserved_prefixes=_SYNC_RESERVED_PREFIXES,
    )


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
    if not isinstance(filename, str):
        filename = str(filename or "")
    return safe_basename(filename, forbidden=_is_forbidden_entry_name)


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

# Host paths that must never become a FileSync root (mesh exfil risk).
_FORBIDDEN_EXTERNAL_PREFIXES = (
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/proc",
    "/sys",
    "/dev",
    "/lib",
    "/lib64",
    "/var/lib",
    "/var/log",
    "/root",
)

_FORBIDDEN_HOME_TOPS = frozenset(
    {
        ".ssh",
        ".gnupg",
        ".aws",
        ".password-store",
        ".reticulum",
        ".config",
        ".local",
    },
)


def _identity_hex(identity) -> str:
    raw = getattr(identity, "hash", None)
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw).hex()
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    return "unknown"


def _is_under_path(candidate: str, root: str) -> bool:
    return is_under_root(candidate, root)


def _looks_like_windows_system_path(resolved: str) -> bool:
    lowered = resolved.replace("/", "\\").lower()
    if lowered.startswith("\\windows") or "\\windows\\system32" in lowered:
        return True
    if len(lowered) >= 3 and lowered[1] == ":" and lowered[2] == "\\":
        drive_tail = lowered[3:]
        if drive_tail.startswith("windows") or drive_tail.startswith("program files"):
            return True
    return False


def _identities_container_for(storage_dir: str) -> str | None:
    parent = os.path.dirname(storage_dir)
    if os.path.basename(parent).lower() == "identities":
        return parent
    return None


def _is_forbidden_external_root(resolved: str) -> bool:
    """Reject host paths that are too broad or system-critical."""
    if "\x00" in resolved:
        return True
    fs_root = os.path.realpath(os.path.abspath(os.sep))
    if resolved == fs_root:
        return True
    home = os.path.expanduser("~")
    if home and home != "~":
        try:
            home_real = os.path.realpath(os.path.abspath(home))
        except OSError:
            home_real = ""
        if home_real and resolved == home_real:
            return True
        if home_real and _is_under_path(resolved, home_real):
            rel = os.path.relpath(resolved, home_real)
            first = rel.split(os.sep, 1)[0]
            if first in _FORBIDDEN_HOME_TOPS:
                return True
    if _looks_like_windows_system_path(resolved):
        return True
    for prefix in _FORBIDDEN_EXTERNAL_PREFIXES:
        if _is_under_path(resolved, prefix):
            return True
    return False


def resolve_sync_directory_path(path: str, identity_storage_dir: str) -> str | None:
    """Resolve a candidate FileSync root for one identity storage tree.

    Relative paths join under identity storage (never process CWD). Absolute and
    ~ paths may be external when they pass the same reserved/sibling/forbidden
    checks used by the live handler.
    """
    cleaned = str(path or "").strip()
    if not cleaned or "\x00" in cleaned:
        return None
    try:
        storage_root = os.path.realpath(identity_storage_dir)
    except OSError:
        return None
    try:
        expanded = os.path.expanduser(cleaned)
        was_relative = not os.path.isabs(expanded)
        if was_relative:
            expanded = os.path.join(storage_root, expanded)
        resolved = os.path.realpath(expanded)
    except OSError:
        return None

    # Relative inputs are identity-scoped only. ../ must not become an
    # accidental external sync root next to storage.
    if was_relative and not _is_under_path(resolved, storage_root):
        return None

    # Never allow a sync root that contains this identity storage (keys/DB).
    if _is_under_path(storage_root, resolved):
        return None

    if _is_under_path(resolved, storage_root):
        rel = os.path.relpath(resolved, storage_root)
        first = rel.split(os.sep, 1)[0]
        if first in _RESERVED_SYNC_TOP or first.endswith(".db"):
            return None
        return resolved

    identities = _identities_container_for(storage_root)
    if identities is not None and _is_under_path(resolved, identities):
        return None

    if _is_forbidden_external_root(resolved):
        return None
    return resolved


def collect_external_filesync_rw_roots(storage_dir: str | None) -> list[str]:
    """Scan identity FileSync settings for sync roots outside global storage.

    Used at Landlock apply time so a previously chosen shared folder stays
    writable after restart. Paths must pass resolve_sync_directory_path for
    that identity. Missing or invalid settings are skipped.
    """
    if not isinstance(storage_dir, str) or not storage_dir.strip():
        return []
    try:
        base = os.path.realpath(os.path.abspath(storage_dir.strip()))
    except OSError:
        return []
    identities = os.path.join(base, "identities")
    if not os.path.isdir(identities):
        return []
    roots: list[str] = []
    try:
        entries = os.listdir(identities)
    except OSError:
        return []
    for name in entries:
        identity_storage = os.path.join(identities, name)
        if not os.path.isdir(identity_storage):
            continue
        settings_path = os.path.join(identity_storage, "filesync", "settings.json")
        if not os.path.isfile(settings_path):
            continue
        data = load_json(settings_path)
        if not isinstance(data, dict):
            continue
        sync_dir = data.get("sync_directory")
        if not isinstance(sync_dir, str) or not sync_dir.strip():
            continue
        resolved = resolve_sync_directory_path(sync_dir, identity_storage)
        if resolved is None:
            continue
        if _is_under_path(resolved, base):
            continue
        if not os.path.isdir(resolved):
            # Create before Landlock restrict so the path can be a RW root.
            try:
                os.makedirs(resolved, exist_ok=True)
            except OSError:
                continue
        if not os.path.isdir(resolved):
            continue
        # Re-check after create/realpath in case of races or symlink swaps.
        verified = resolve_sync_directory_path(resolved, identity_storage)
        if verified is None or verified != os.path.realpath(resolved):
            continue
        if verified not in roots:
            roots.append(verified)
    return roots


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

    def _identities_container(self) -> str | None:
        return _identities_container_for(self.storage_dir)

    def _resolve_sync_directory(self, path: str) -> str | None:
        """Resolve a candidate sync root.

        Allowed:
        - Under this identity storage, excluding reserved tops and the identity root
        - Outside identity storage, when not a forbidden host path and not another
          identity's storage tree

        CRUD under the chosen root stays jailed via _resolve_manager_path.
        """
        return resolve_sync_directory_path(path, self.storage_dir)

    def suggest_shared_sync_directory(self) -> dict[str, Any]:
        """Suggest a per-identity folder outside app-private storage.

        On Android this targets public Documents so other apps can open files.
        Desktop uses ~/Documents/MeshChatX/<full-identity-hash>/sync.
        """
        identity_id = _identity_hex(self.identity)
        android = False
        try:
            from meshchatx.android_push_bridge import _is_chaquopy_android

            android = bool(_is_chaquopy_android())
        except Exception:
            android = False
        if android:
            base = "/storage/emulated/0/Documents/MeshChatX"
        else:
            base = os.path.join(os.path.expanduser("~"), "Documents", "MeshChatX")
        path = os.path.join(base, identity_id, "sync")
        resolved = self._resolve_sync_directory(path)
        if resolved is None:
            return err_result(
                "shared sync directory not allowed",
                path=path,
                android=android,
            )
        return ok_result(
            path=resolved,
            android=android,
            requires_all_files_access=android,
        )

    def _sync_root(self) -> str:
        """Real path of the configured sync directory (file manager jail base)."""
        os.makedirs(self._sync_directory, exist_ok=True)
        return os.path.realpath(self._sync_directory)

    def _is_under_sync_root(self, candidate: str) -> bool:
        root = self._sync_root()
        real = os.path.realpath(candidate)
        return is_under_root(real, root)

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
        try:
            safe_rel = _normalize_sync_relpath(cleaned)
        except PathJailError:
            return None, "path not allowed"

        parts = safe_rel.replace("\\", "/").split("/")
        if any(_is_forbidden_entry_name(part) for part in parts):
            return None, "path not allowed"

        try:
            real = resolve_under_root(
                root,
                safe_rel,
                allow_root=allow_root,
                must_exist=must_exist,
                check_symlinked_parents=True,
            )
        except PathJailError as exc:
            if exc.reason == "not_found":
                return None, "path not found"
            return None, "path not allowed"
        return real, None

    def _relpath_under_sync(self, abspath: str) -> str | None:
        try:
            return relative_to_root(
                self._sync_root(),
                abspath,
                reserved_names=_SYNC_RESERVED_NAMES,
                reserved_prefixes=_SYNC_RESERVED_PREFIXES,
            )
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
                return err_result(err or "path not allowed")
            if not os.path.isdir(target):
                return err_result("not a directory")

            root = self._sync_root()
            entries: list[dict[str, Any]] = []
            try:
                names = sorted(os.listdir(target), key=str.lower)
            except OSError as exc:
                return err_result_from(exc)

            for name in names:
                if _is_forbidden_entry_name(name):
                    continue
                full = os.path.join(target, name)
                real = os.path.realpath(full)
                if not is_under_root(real, root):
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

            return ok_result(
                root=root,
                current=current_rel,
                parent=parent_rel,
                entries=entries,
            )

    def manager_mkdir(self, path: str) -> dict[str, Any]:
        """Create a directory under the sync root (relative path)."""
        with self._lock:
            cleaned = str(path or "").strip()
            if not cleaned:
                return err_result("path is required")
            # Resolve parent and create leaf so we do not require the leaf to exist.
            try:
                safe_rel = _normalize_sync_relpath(cleaned)
            except PathJailError:
                return err_result("path not allowed")
            parts = safe_rel.replace("\\", "/").split("/")
            if any(_is_forbidden_entry_name(part) for part in parts):
                return err_result("path not allowed")
            leaf = parts[-1]
            parent_rel = "/".join(parts[:-1]) if len(parts) > 1 else ""
            parent_abs, err = self._resolve_manager_path(
                parent_rel or None,
                allow_root=True,
                must_exist=True,
            )
            if err or parent_abs is None:
                return err_result(err or "path not allowed")
            if not os.path.isdir(parent_abs):
                return err_result("parent is not a directory")
            if os.path.islink(parent_abs):
                return err_result("path not allowed")

            new_path = os.path.join(parent_abs, leaf)
            if not self._is_under_sync_root(os.path.dirname(new_path)):
                return err_result("path not allowed")
            if os.path.lexists(new_path):
                return err_result("already exists")
            try:
                os.mkdir(new_path)
            except OSError as exc:
                return err_result_from(exc)
            real = os.path.realpath(new_path)
            if not self._is_under_sync_root(real):
                with contextlib.suppress(OSError):
                    os.rmdir(new_path)
                return err_result("path not allowed")
            rel = self._relpath_under_sync(real) or safe_rel
            return ok_result(path=rel)

    def _resolve_upload_dest(
        self,
        filename: str | None,
        subdir: str | None,
    ) -> tuple[str | None, str | None]:
        """Validate an upload target and return (dest abspath, error)."""
        base = _sanitize_upload_basename(filename)
        if base is None:
            return None, "invalid filename"

        parent_abs, err = self._resolve_manager_path(
            subdir,
            allow_root=True,
            must_exist=True,
        )
        if err or parent_abs is None:
            return None, err or "path not allowed"
        if not os.path.isdir(parent_abs) or os.path.islink(parent_abs):
            return None, "path not allowed"

        dest = os.path.join(parent_abs, base)
        if os.path.islink(dest):
            return None, "path not allowed"
        if os.path.lexists(dest):
            real_existing = os.path.realpath(dest)
            if not self._is_under_sync_root(real_existing):
                return None, "path not allowed"
        return dest, None

    def _finalize_upload(self, dest: str, size: int) -> dict[str, Any]:
        """Re-verify a written upload stayed jailed, then nudge inventory."""
        real = os.path.realpath(dest)
        if not self._is_under_sync_root(real) or not os.path.isfile(real):
            with contextlib.suppress(OSError):
                os.unlink(dest)
            return err_result("path not allowed")
        rel = self._relpath_under_sync(real)
        if rel is None:
            with contextlib.suppress(OSError):
                os.unlink(dest)
            return err_result("path not allowed")
        self._nudge_inventory(rel)
        return ok_result(path=rel, size=size)

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
                return err_result("invalid upload data")
            if len(data) > MANAGER_UPLOAD_MAX_BYTES:
                return err_result("upload too large")
            dest, err = self._resolve_upload_dest(filename, subdir)
            if err or dest is None:
                return err_result(err or "path not allowed")
            try:
                atomic_write_bytes(dest, data)
            except OSError as exc:
                return err_result_from(exc, "upload failed")
            return self._finalize_upload(dest, len(data))

    def manager_upload_staging_path(self) -> str:
        """Create an empty tmp file under the sync root for a streamed upload.

        The .rns-xfer- sidecar prefix keeps a leftover staging file out of
        inventory scans and manager listings. Every upload destination sits
        under the same sync root, so the later os.replace stays atomic on
        one filesystem.
        """
        with self._lock:
            root = self._sync_root()
            fd, tmp = tempfile.mkstemp(
                prefix=".rns-xfer-upload-",
                suffix=".tmp",
                dir=root,
            )
            os.close(fd)
            return tmp

    def manager_upload_file(
        self,
        *,
        filename: str | None,
        src_path: str | None,
        subdir: str | None = None,
    ) -> dict[str, Any]:
        """Move a file staged via manager_upload_staging_path into place."""
        with self._lock:
            if not isinstance(src_path, str) or not src_path:
                return err_result("invalid upload data")
            staged = os.path.realpath(src_path)
            if (
                os.path.dirname(staged) != self._sync_root()
                or not os.path.basename(staged).startswith(".rns-xfer-upload-")
                or not os.path.isfile(staged)
            ):
                return err_result("invalid upload data")
            size = os.path.getsize(staged)
            if size > MANAGER_UPLOAD_MAX_BYTES:
                with contextlib.suppress(OSError):
                    os.unlink(staged)
                return err_result("upload too large")

            dest, err = self._resolve_upload_dest(filename, subdir)
            if err or dest is None:
                with contextlib.suppress(OSError):
                    os.unlink(staged)
                return err_result(err or "path not allowed")

            try:
                with open(staged, "r+b") as handle:
                    os.fsync(handle.fileno())
                os.replace(staged, dest)
            except OSError as exc:
                with contextlib.suppress(OSError):
                    os.unlink(staged)
                return err_result_from(exc, "upload failed")
            _fsync_dir(os.path.dirname(dest))
            return self._finalize_upload(dest, size)

    def manager_delete(self, path: str) -> dict[str, Any]:
        """Delete a file or empty directory under the sync root."""
        with self._lock:
            root = self._sync_root()
            try:
                safe_rel = _normalize_sync_relpath(str(path or "").strip())
            except PathJailError:
                return err_result("path not allowed")
            lex_path = os.path.join(root, safe_rel)
            if os.path.islink(lex_path):
                return err_result("path not allowed")

            target, err = self._resolve_manager_path(
                path,
                allow_root=False,
                must_exist=True,
            )
            if err or target is None:
                return err_result(err or "path not allowed")
            if target == root:
                return err_result("path not allowed")

            rel = self._relpath_under_sync(target)
            if rel is None:
                return err_result("path not allowed")

            try:
                if os.path.isdir(target):
                    try:
                        os.rmdir(target)
                    except OSError:
                        return err_result("directory is not empty")
                elif os.path.isfile(target):
                    os.unlink(target)
                else:
                    return err_result("path not found")
            except OSError as exc:
                return err_result_from(exc)

            self._nudge_inventory(rel)
            return ok_result(path=rel)

    def manager_content(self, path: str) -> dict[str, Any]:
        """Resolve a file under the sync root for download streaming."""
        with self._lock:
            root = self._sync_root()
            try:
                safe_rel = _normalize_sync_relpath(str(path or "").strip())
            except PathJailError:
                return err_result("path not allowed")
            lex_path = os.path.join(root, safe_rel)
            if os.path.islink(lex_path):
                return err_result("path not allowed")

            target, err = self._resolve_manager_path(
                path,
                allow_root=False,
                must_exist=True,
            )
            if err or target is None:
                return err_result(err or "path not allowed")
            if not os.path.isfile(target):
                return err_result("not a file")
            rel = self._relpath_under_sync(target)
            if rel is None:
                return err_result("path not allowed")
            return ok_result(
                abspath=target,
                path=rel,
                filename=os.path.basename(target),
                size=os.path.getsize(target),
            )

    def _load_settings(self) -> None:
        os.makedirs(self._root, exist_ok=True)
        if not os.path.isfile(self._settings_path):
            return
        data = load_json(self._settings_path)
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
        save_json(self._settings_path, payload, sort_keys=True)

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
        atomic_write_text(self._acl_path, "\n".join(lines) + "\n")
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
        """List subdirectories for the sync-folder picker.

        Default browse root is identity filesync config. Absolute paths that
        pass _resolve_sync_directory (including shared external folders) are
        also browsable.
        """
        with self._lock:
            identity_root = self.storage_dir
            cleaned = str(path or "").strip()
            if cleaned:
                target = self._resolve_sync_directory(cleaned)
                if target is None:
                    return err_result("path not allowed for sync directory")
                under_identity = _is_under_path(target, identity_root)
            else:
                os.makedirs(self._root, exist_ok=True)
                target = self._root
                under_identity = True

            if not os.path.isdir(target):
                cursor = target
                while True:
                    parent = os.path.dirname(cursor)
                    if parent == cursor:
                        break
                    if under_identity:
                        if parent != identity_root and not _is_under_path(
                            parent,
                            identity_root,
                        ):
                            break
                    else:
                        if self._resolve_sync_directory(parent) is None:
                            break
                    cursor = parent
                    if os.path.isdir(cursor):
                        target = cursor
                        break
                if not os.path.isdir(target):
                    if under_identity:
                        os.makedirs(self._root, exist_ok=True)
                        target = self._root
                    else:
                        return err_result("directory does not exist")

            entries: list[dict[str, str]] = []
            try:
                for name in sorted(os.listdir(target), key=str.lower):
                    if name.startswith("."):
                        continue
                    full = os.path.join(target, name)
                    if not os.path.isdir(full):
                        continue
                    resolved = os.path.realpath(full)
                    if self._resolve_sync_directory(resolved) is None:
                        continue
                    entries.append({"name": name, "path": resolved})
            except OSError as exc:
                return err_result_from(exc)

            current = os.path.realpath(target)
            parent = None
            if under_identity:
                if current != identity_root:
                    candidate = os.path.dirname(current)
                    if candidate == identity_root or _is_under_path(
                        candidate,
                        identity_root,
                    ):
                        parent = candidate
            else:
                candidate = os.path.dirname(current)
                if (
                    candidate != current
                    and self._resolve_sync_directory(candidate) is not None
                ):
                    parent = candidate

            return ok_result(
                root=identity_root if under_identity else current,
                current=current,
                parent=parent,
                directories=entries,
            )

    def create_directory(self, parent: str | None, name: str) -> dict[str, Any]:
        """Create a subdirectory for use as a sync folder."""
        with self._lock:
            cleaned_name = str(name or "").strip()
            if (
                not cleaned_name
                or cleaned_name in (".", "..")
                or "/" in cleaned_name
                or "\\" in cleaned_name
                or cleaned_name.startswith(".")
            ):
                return err_result("invalid directory name")

            parent_cleaned = str(parent or "").strip()
            if parent_cleaned:
                parent_resolved = self._resolve_sync_directory(parent_cleaned)
            else:
                os.makedirs(self._root, exist_ok=True)
                parent_resolved = self._root
            if parent_resolved is None:
                return err_result("parent not allowed for sync directory")

            new_path = os.path.join(parent_resolved, cleaned_name)
            resolved = self._resolve_sync_directory(new_path)
            if resolved is None:
                return err_result("path not allowed for sync directory")
            try:
                os.makedirs(resolved, exist_ok=False)
            except FileExistsError:
                return err_result("directory already exists")
            except OSError as exc:
                return err_result_from(exc)
            return ok_result(path=resolved)

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
                    return err_result("sync_directory not allowed")
                self._sync_directory = resolved
            if monitor is not None:
                self._monitor = bool(monitor)
            if announce_interval is not None:
                try:
                    interval = int(announce_interval)
                except (TypeError, ValueError):
                    return err_result("invalid announce_interval")
                if interval < 10:
                    return err_result("announce_interval must be >= 10")
                self._announce_interval = interval

            if self.service is not None:
                status = self.service.get_status()
                if status.get("running"):
                    return ok_result(already_running=True, **status)

            try:
                os.makedirs(self._sync_directory, exist_ok=True)
            except OSError as exc:
                return err_result(
                    "cannot create sync directory "
                    f"({exc}). If Landlock is active, restart MeshChatX "
                    "after choosing a shared folder outside identity storage."
                )
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
                return ok_result(running=False)
            with contextlib.suppress(Exception):
                self.service.stop()
            self.service = None
            return ok_result(running=False)

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
                return err_result("filesync is not running")
            cleaned = _normalize_peer_hash(identity_hash)
            if cleaned is None or cleaned == "all":
                return err_result("invalid identity_hash")
            return self.service.connect_peer(cleaned)

    def disconnect_peer(self, peer_id: str) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return err_result("filesync is not running")
            cleaned = str(peer_id or "").strip()
            if not cleaned:
                return err_result("peer_id is required")
            self.service.disconnect_peer(cleaned)
            return ok_result(peer_id=cleaned)

    def announce_now(self) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return err_result("filesync is not running")
            self.service.announce_now()
            return ok_result()

    def browse_peer(self, peer_id: str, timeout: float = 10.0) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return err_result("filesync is not running", files=[])
            cleaned = str(peer_id or "").strip()
            if not cleaned:
                return err_result("peer_id is required", files=[])
            try:
                timeout_f = float(timeout)
            except (TypeError, ValueError):
                timeout_f = 10.0
            timeout_f = max(timeout_f, 0.1)
            timeout_f = min(timeout_f, 120.0)
            files = self.service.browse_peer(cleaned, timeout=timeout_f)
            return ok_result(peer_id=cleaned, files=files)

    def download_file(self, peer_id: str, path: str) -> dict[str, Any]:
        with self._lock:
            if self.service is None:
                return err_result("filesync is not running")
            cleaned_peer = str(peer_id or "").strip()
            cleaned_path = str(path or "").strip()
            if not cleaned_peer:
                return err_result("peer_id is required")
            if not cleaned_path:
                return err_result("path is required")
            try:
                safe_path = _normalize_sync_relpath(cleaned_path)
            except PathJailError as exc:
                return err_result_from(exc)
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
                    return err_result("invalid identity_hash")
                granted = permissions.grant(peer, perms)
                if not granted and perms:
                    return err_result("no valid permissions provided")

            if enforce is not None:
                permissions._enforce = bool(enforce)

            if self.service is not None:
                self.service.permissions = permissions

            self._save_acl(permissions)
            return ok_result(
                enforce=permissions.enabled,
                rules=permissions.as_dict(),
            )

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
                    return err_result("stop filesync before changing sync directory")
                resolved = self._resolve_sync_directory(sync_directory)
                if resolved is None:
                    return err_result("sync_directory not allowed")
                self._sync_directory = resolved

            if monitor is not None:
                self._monitor = bool(monitor)

            if announce_interval is not None:
                try:
                    interval = int(announce_interval)
                except (TypeError, ValueError):
                    return err_result("invalid announce_interval")
                if interval < 10:
                    return err_result("announce_interval must be >= 10")
                self._announce_interval = interval

            self._save_settings()
            return ok_result(
                sync_directory=self._sync_directory,
                monitor=self._monitor,
                announce_interval=self._announce_interval,
                running=running,
            )
