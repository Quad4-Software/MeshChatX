# SPDX-License-Identifier: 0BSD

"""Pick a compatible on-disk backup and run SQLite recovery when backups are unavailable."""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from meshchatx.src.backend.database import Database, PRE_MIGRATE_BACKUP_PREFIX
from meshchatx.src.backend.database.provider import DatabaseProvider

_SUSPICIOUS_RE = re.compile(r"SUSPICIOUS", re.I)
_PRE_MIGRATE_VERSION_RE = re.compile(
    rf"{re.escape(PRE_MIGRATE_BACKUP_PREFIX)}v(\d+)-to-v(\d+)",
    re.I,
)


@dataclass(frozen=True)
class RecoveryBackupCandidate:
    name: str
    path: str
    created_at: str
    kind: str
    suspicious: bool


def list_recovery_backup_candidates(storage_path: str) -> list[RecoveryBackupCandidate]:
    if not storage_path:
        return []
    entries: list[RecoveryBackupCandidate] = []
    for kind, subdir in (("auto", "database-backups"), ("snapshot", "snapshots")):
        directory = os.path.join(storage_path, subdir)
        if not os.path.isdir(directory):
            continue
        for name in os.listdir(directory):
            if not name.endswith(".zip"):
                continue
            full_path = os.path.join(directory, name)
            if not os.path.isfile(full_path):
                continue
            stats = os.stat(full_path)
            entries.append(
                RecoveryBackupCandidate(
                    name=name,
                    path=full_path,
                    created_at=datetime.fromtimestamp(stats.st_mtime, UTC).isoformat(),
                    kind=kind,
                    suspicious=bool(_SUSPICIOUS_RE.search(name)),
                ),
            )
    return sorted(entries, key=lambda row: row.created_at, reverse=True)


def read_schema_version_from_db_path(db_path: str) -> int | None:
    provider = DatabaseProvider(db_path)
    try:
        row = provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("database_version",),
        )
        if not row:
            return 0
        return int(row["value"])
    except (TypeError, ValueError):
        return None
    except Exception:
        return None
    finally:
        provider.close_all()


def infer_version_hint_from_backup_name(name: str) -> int | None:
    match = _PRE_MIGRATE_VERSION_RE.search(name)
    if not match:
        return None
    try:
        return int(match.group(2))
    except ValueError:
        return None


def schema_version_restorable(version: int | None, latest_schema_version: int) -> bool:
    if version is None:
        return False
    return 0 <= version <= latest_schema_version


def _quick_check_label(provider: DatabaseProvider) -> str:
    rows = provider.quick_check()
    if not rows:
        return "unknown"
    first = rows[0]
    if isinstance(first, dict):
        return str(next(iter(first.values())))
    return str(first[0])


def _find_primary_db_member(zf: zipfile.ZipFile) -> str | None:
    members: list[str] = []
    for member in zf.namelist():
        if member.endswith("/"):
            continue
        base = os.path.basename(member)
        if base.endswith(".db") and not base.endswith(("-wal", "-shm")):
            members.append(member)
    if not members:
        return None
    return sorted(members, key=lambda name: name.count("/"))[0]


def probe_backup_zip(zip_path: str) -> dict[str, Any]:
    if not os.path.isfile(zip_path):
        return {"version": None, "quick_check": None, "error": "backup file not found"}
    if not zipfile.is_zipfile(zip_path):
        return {"version": None, "quick_check": None, "error": "not a zip backup"}

    with tempfile.TemporaryDirectory(prefix="meshchatx-backup-probe-") as tmp:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                member = _find_primary_db_member(zf)
                if not member:
                    return {
                        "version": None,
                        "quick_check": None,
                        "error": "no database file in backup",
                    }
                Database._safe_zip_extract_member(zf, member, tmp)
            db_path = os.path.join(tmp, os.path.basename(member))
            if not os.path.isfile(db_path):
                found: str | None = None
                for root, _, files in os.walk(tmp):
                    for name in files:
                        if name.endswith(".db") and not name.endswith(("-wal", "-shm")):
                            found = os.path.join(root, name)
                            break
                    if found:
                        break
                db_path = found
            if not db_path or not os.path.isfile(db_path):
                return {
                    "version": None,
                    "quick_check": None,
                    "error": "extracted database missing",
                }
            version = read_schema_version_from_db_path(db_path)
            provider = DatabaseProvider(db_path)
            try:
                quick_check = _quick_check_label(provider)
            finally:
                provider.close_all()
            return {"version": version, "quick_check": quick_check, "error": None}
        except Exception as exc:
            return {"version": None, "quick_check": None, "error": str(exc)}


def pick_compatible_backup(
    storage_path: str,
    latest_schema_version: int,
) -> dict[str, Any] | None:
    candidates = list_recovery_backup_candidates(storage_path)
    healthy = [row for row in candidates if not row.suspicious]
    ordered = healthy if healthy else list(candidates)

    for candidate in ordered:
        probe = probe_backup_zip(candidate.path)
        version = probe.get("version")
        if version is None:
            version = infer_version_hint_from_backup_name(candidate.name)
        if not schema_version_restorable(version, latest_schema_version):
            continue
        quick_check = probe.get("quick_check")
        if quick_check is not None and quick_check != "ok":
            continue
        if probe.get("error") and version is None:
            continue
        return {
            "name": candidate.name,
            "path": candidate.path,
            "kind": candidate.kind,
            "database_version": version,
            "quick_check": quick_check,
            "suspicious": candidate.suspicious,
        }
    return None


def run_auto_database_recover(
    storage_path: str,
    db_path: str | None,
    latest_schema_version: int,
    restore_fn: Callable[[str], dict],
    sqlite_recover_fn: Callable[[], dict] | None = None,
) -> dict[str, Any]:
    picked = pick_compatible_backup(storage_path, latest_schema_version)
    if picked:
        restore_result = restore_fn(picked["path"])
        return {
            "strategy": "restore_backup",
            "message": f"Restored database from {picked['name']}",
            "backup": picked,
            "requires_relaunch": True,
            "restore_result": restore_result,
        }

    if sqlite_recover_fn is not None and db_path and os.path.isfile(db_path):
        try:
            recovery = sqlite_recover_fn()
            return {
                "strategy": "sqlite_recovery",
                "message": "SQLite recovery routine completed on the live database",
                "requires_relaunch": False,
                "database": recovery,
            }
        except Exception as exc:
            return {
                "strategy": "none",
                "message": (
                    "No compatible automatic backup was found and SQLite recovery failed"
                ),
                "requires_relaunch": False,
                "error": str(exc),
            }

    return {
        "strategy": "none",
        "message": (
            "No compatible automatic backup was found. Use Restore from file or "
            "pick a snapshot manually."
        ),
        "requires_relaunch": False,
    }
