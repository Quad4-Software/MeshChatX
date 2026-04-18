# SPDX-License-Identifier: 0BSD

import json
import logging
import os
import shutil
import zipfile
from datetime import UTC, datetime

from .access_attempts import AccessAttemptsDAO
from .announces import AnnounceDAO
from .config import ConfigDAO
from .contacts import ContactsDAO
from .crash_history import CrashHistoryDAO
from .debug_logs import DebugLogsDAO
from .gifs import UserGifsDAO
from .legacy_migrator import LegacyMigrator
from .map_drawings import MapDrawingsDAO
from .messages import MessageDAO
from .misc import MiscDAO
from .provider import DatabaseProvider
from .ringtones import RingtoneDAO
from .schema import DatabaseSchema
from .sticker_packs import UserStickerPacksDAO
from .stickers import UserStickersDAO
from .telemetry import TelemetryDAO
from .telephone import TelephoneDAO
from .voicemails import VoicemailDAO

BACKUP_BASELINE_FILENAME = "backup-baseline.json"
MIN_SIZE_RATIO = 0.2

_log = logging.getLogger("meshchatx.database")


class Database:
    def __init__(self, db_path):
        self.provider = DatabaseProvider.get_instance(db_path)
        self.schema = DatabaseSchema(self.provider)
        self.config = ConfigDAO(self.provider)
        self.messages = MessageDAO(self.provider)
        self.announces = AnnounceDAO(self.provider)
        self.misc = MiscDAO(self.provider)
        self.telephone = TelephoneDAO(self.provider)
        self.telemetry = TelemetryDAO(self.provider)
        self.voicemails = VoicemailDAO(self.provider)
        self.ringtones = RingtoneDAO(self.provider)
        self.contacts = ContactsDAO(self.provider)
        self.map_drawings = MapDrawingsDAO(self.provider)
        self.stickers = UserStickersDAO(self.provider)
        self.sticker_packs = UserStickerPacksDAO(self.provider)
        self.gifs = UserGifsDAO(self.provider)
        self.debug_logs = DebugLogsDAO(self.provider)
        self.access_attempts = AccessAttemptsDAO(self.provider)
        self.crash_history = CrashHistoryDAO(self.provider)

    def initialize(self):
        self._tune_sqlite_pragmas()
        self.schema.initialize()

    def migrate_from_legacy(self, reticulum_config_dir, identity_hash_hex):
        migrator = LegacyMigrator(
            self.provider,
            reticulum_config_dir,
            identity_hash_hex,
        )
        if migrator.should_migrate():
            return migrator.migrate()
        return False

    def execute_sql(self, query, params=None):
        return self.provider.execute(query, params)

    def _tune_sqlite_pragmas(self):
        try:
            self.execute_sql("PRAGMA journal_mode=WAL")
            self.execute_sql("PRAGMA synchronous=NORMAL")
            self.execute_sql("PRAGMA wal_autocheckpoint=1000")
            self.execute_sql("PRAGMA temp_store=MEMORY")
            self.execute_sql("PRAGMA cache_size=-8000")  # 8 MB
            self.execute_sql("PRAGMA mmap_size=67108864")  # 64 MB
            self.execute_sql("PRAGMA busy_timeout=5000")  # 5 s wait on lock contention
        except Exception as exc:
            print(f"SQLite pragma setup failed: {exc}")

    def _get_pragma_value(self, pragma: str, default=None):
        try:
            cursor = self.execute_sql(f"PRAGMA {pragma}")
            row = cursor.fetchone()
            if row is None:
                return default
            return row[0]
        except Exception:
            return default

    def _get_database_file_stats(self):
        def size_for(path):
            try:
                return os.path.getsize(path)
            except OSError:
                return 0

        db_path = self.provider.db_path
        wal_path = f"{db_path}-wal"
        shm_path = f"{db_path}-shm"

        main_bytes = size_for(db_path)
        wal_bytes = size_for(wal_path)
        shm_bytes = size_for(shm_path)

        return {
            "main_bytes": main_bytes,
            "wal_bytes": wal_bytes,
            "shm_bytes": shm_bytes,
            "total_bytes": main_bytes + wal_bytes + shm_bytes,
        }

    def _get_backup_baseline_path(self, storage_path):
        default_dir = os.path.join(storage_path, "database-backups")
        return os.path.join(default_dir, BACKUP_BASELINE_FILENAME)

    def _read_backup_baseline(self, storage_path):
        path = self._get_backup_baseline_path(storage_path)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return data
        except (OSError, json.JSONDecodeError):
            return None

    def _write_backup_baseline(self, storage_path, message_count, total_bytes):
        path = self._get_backup_baseline_path(storage_path)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {
                "message_count": message_count,
                "total_bytes": total_bytes,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"Failed to write backup baseline: {e}")

    def _get_current_db_content_stats(self):
        stats = self._get_database_file_stats()
        try:
            message_count = self.messages.count_lxmf_messages()
        except Exception:
            message_count = -1
        return {
            "message_count": message_count,
            "total_bytes": stats["total_bytes"],
        }

    def _is_backup_suspicious(self, current_stats, baseline):
        if not baseline:
            return False
        prev_count = baseline.get("message_count", 0)
        prev_bytes = baseline.get("total_bytes", 0)
        curr_count = current_stats.get("message_count", 0)
        curr_bytes = current_stats.get("total_bytes", 0)
        if prev_count > 0 and curr_count == 0:
            return True
        if prev_bytes > 100_000 and curr_bytes < prev_bytes * MIN_SIZE_RATIO:
            return True
        return False

    def check_db_health_at_open(self, storage_path):
        """Run integrity and baseline checks after opening the database.

        Returns human-readable issue strings; empty if healthy.
        """
        issues = []
        try:
            integrity_rows = self.provider.integrity_check()
            if not integrity_rows:
                issues.append("Database integrity check failed: no result")
                _log.warning("DB open health check: no result")
            else:
                first = integrity_rows[0]
                val = list(first.values())[0] if isinstance(first, dict) else first[0]
                if val != "ok":
                    issues.append(f"Database integrity check failed: {val!s}")
                    _log.warning("DB open health check: %s", val)
        except Exception as e:
            msg = f"Database integrity check error: {e!s}"
            issues.append(msg)
            _log.warning("DB open health check: %s", msg)

        try:
            current = self._get_current_db_content_stats()
            baseline = self._read_backup_baseline(storage_path)
            if self._is_backup_suspicious(current, baseline):
                prev_c = baseline.get("message_count", 0)
                prev_b = baseline.get("total_bytes", 0)
                curr_c = current.get("message_count", 0)
                curr_b = current.get("total_bytes", 0)
                msg = (
                    f"Database content anomaly: was {prev_c} messages / {prev_b} bytes, "
                    f"now {curr_c} / {curr_b}. Restore from backup if needed."
                )
                issues.append(msg)
                _log.warning("DB open health check: %s", msg)
            else:
                _log.info(
                    "DB open health check ok: messages=%s total_bytes=%s",
                    current.get("message_count"),
                    current.get("total_bytes"),
                )
        except Exception as e:
            _log.warning("DB open health check (baseline): %s", e)

        return issues

    def check_db_health_at_close(self, storage_path):
        """Run health checks before closing the database (for logging only).

        Returns issue strings; empty if healthy.
        """
        issues = []
        try:
            integrity_rows = self.provider.integrity_check()
            if not integrity_rows:
                issues.append("Database integrity check failed: no result")
                _log.warning("DB close health check: no result")
            else:
                first = integrity_rows[0]
                val = list(first.values())[0] if isinstance(first, dict) else first[0]
                if val != "ok":
                    issues.append(f"Database integrity check failed: {val!s}")
                    _log.warning("DB close health check: integrity failed")
        except Exception as e:
            _log.warning("DB close health check: %s", e)

        try:
            current = self._get_current_db_content_stats()
            baseline = self._read_backup_baseline(storage_path)
            if self._is_backup_suspicious(current, baseline):
                issues.append(
                    "Database content anomaly detected at close. Consider restoring from backup.",
                )
                _log.warning("DB close health check: content anomaly")
            else:
                _log.info(
                    "DB close health check ok: messages=%s total_bytes=%s",
                    current.get("message_count"),
                    current.get("total_bytes"),
                )
        except Exception as e:
            _log.warning("DB close health check (baseline): %s", e)

        return issues

    def _database_paths(self):
        db_path = self.provider.db_path
        return {
            "main": db_path,
            "wal": f"{db_path}-wal",
            "shm": f"{db_path}-shm",
        }

    def get_database_health_snapshot(self):
        page_size = self._get_pragma_value("page_size", 0) or 0
        page_count = self._get_pragma_value("page_count", 0) or 0
        freelist_pages = self._get_pragma_value("freelist_count", 0) or 0
        freelist_bytes = (
            page_size * freelist_pages if page_size > 0 and freelist_pages > 0 else 0
        )
        if freelist_bytes > 0:
            free_bytes = freelist_bytes
        else:
            try:
                db_dir = os.path.dirname(os.path.abspath(self.provider.db_path))
                free_bytes = shutil.disk_usage(db_dir).free if db_dir else 0
            except OSError:
                free_bytes = 0

        return {
            "quick_check": self._get_pragma_value("quick_check", "unknown"),
            "journal_mode": self._get_pragma_value("journal_mode", "unknown"),
            "synchronous": self._get_pragma_value("synchronous", None),
            "wal_autocheckpoint": self._get_pragma_value("wal_autocheckpoint", None),
            "auto_vacuum": self._get_pragma_value("auto_vacuum", None),
            "page_size": page_size,
            "page_count": page_count,
            "freelist_pages": freelist_pages,
            "estimated_free_bytes": free_bytes,
            "files": self._get_database_file_stats(),
        }

    def _checkpoint_wal(self, mode: str = "TRUNCATE"):
        return self.execute_sql(f"PRAGMA wal_checkpoint({mode})").fetchall()

    def run_database_vacuum(self):
        try:
            # Attempt to checkpoint WAL, ignore errors if busy
            try:
                self._checkpoint_wal()
            except Exception as e:
                print(
                    f"Warning: WAL checkpoint during vacuum failed (non-critical): {e}",
                )

            self.execute_sql("VACUUM")
            self._tune_sqlite_pragmas()

            return {
                "health": self.get_database_health_snapshot(),
            }
        except Exception as e:
            # Wrap in a cleaner error message
            raise Exception(f"Database vacuum failed: {e!s}")

    def run_database_recovery(self):
        actions = []

        actions.append(
            {
                "step": "quick_check_before",
                "result": self._get_pragma_value("quick_check", "unknown"),
            },
        )

        actions.append({"step": "wal_checkpoint", "result": self._checkpoint_wal()})

        integrity_rows = self.provider.integrity_check()
        integrity = [row[0] for row in integrity_rows] if integrity_rows else []
        actions.append({"step": "integrity_check", "result": integrity})

        self.provider.vacuum()
        self._tune_sqlite_pragmas()

        actions.append(
            {
                "step": "quick_check_after",
                "result": self._get_pragma_value("quick_check", "unknown"),
            },
        )

        return {
            "actions": actions,
            "health": self.get_database_health_snapshot(),
        }

    def _checkpoint_and_close(self):
        try:
            self._checkpoint_wal()
        except Exception as e:
            print(f"Failed to checkpoint WAL: {e}")
        try:
            self.close()
        except Exception as e:
            print(f"Failed to close database: {e}")

    def close(self):
        if hasattr(self, "provider"):
            self.provider.close()

    def close_all(self):
        if hasattr(self, "provider"):
            self.provider.close_all()

    def _backup_to_zip(self, backup_path: str):
        paths = self._database_paths()
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        # ensure WAL is checkpointed to get a consistent snapshot
        self._checkpoint_wal()

        main_filename = os.path.basename(paths["main"])
        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(paths["main"], arcname=main_filename)
            if os.path.exists(paths["wal"]):
                zf.write(paths["wal"], arcname=f"{main_filename}-wal")
            if os.path.exists(paths["shm"]):
                zf.write(paths["shm"], arcname=f"{main_filename}-shm")

        return {
            "path": backup_path,
            "size": os.path.getsize(backup_path),
        }

    def backup_database(
        self,
        storage_path,
        backup_path: str | None = None,
        max_count: int | None = None,
    ):
        default_dir = os.path.join(storage_path, "database-backups")
        os.makedirs(default_dir, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        current_stats = self._get_current_db_content_stats()
        baseline = self._read_backup_baseline(storage_path)
        suspicious = self._is_backup_suspicious(current_stats, baseline)

        if backup_path is None:
            if suspicious:
                backup_path = os.path.join(
                    default_dir,
                    f"backup-SUSPICIOUS-{timestamp}.zip",
                )
            else:
                backup_path = os.path.join(default_dir, f"backup-{timestamp}.zip")

        result = self._backup_to_zip(backup_path)

        if suspicious:
            _log.warning(
                "Backup data-loss guard: current DB looks wrong (was %s messages / %s bytes, now %s / %s); "
                "wrote backup-SUSPICIOUS-*.zip, skipping rotation",
                baseline.get("message_count"),
                baseline.get("total_bytes"),
                current_stats.get("message_count"),
                current_stats.get("total_bytes"),
            )
            print(
                "Backup data-loss guard: current database looks wrong "
                f"(was {baseline.get('message_count')} messages / {baseline.get('total_bytes')} bytes, "
                f"now {current_stats.get('message_count')} / {current_stats.get('total_bytes')}). "
                "Wrote backup-SUSPICIOUS-*.zip; skipping rotation and baseline update. Check disk and DB.",
            )
            result["suspicious"] = True
            result["baseline"] = baseline
            result["current_stats"] = current_stats
            return result

        if max_count is not None and max_count > 0:
            try:
                backups = []
                for file in os.listdir(default_dir):
                    if (
                        file.endswith(".zip")
                        and file.startswith("backup-")
                        and "SUSPICIOUS" not in file
                    ):
                        full_path = os.path.join(default_dir, file)
                        stats = os.stat(full_path)
                        backups.append((full_path, stats.st_mtime))

                if len(backups) > max_count:
                    backups.sort(key=lambda x: x[1])
                    to_delete = backups[: len(backups) - max_count]
                    for path, _ in to_delete:
                        if os.path.exists(path):
                            os.remove(path)
            except Exception as e:
                print(f"Failed to cleanup old backups: {e}")

        self._write_backup_baseline(
            storage_path,
            current_stats["message_count"],
            current_stats["total_bytes"],
        )
        return result

    def create_snapshot(self, storage_path, name: str):
        """Creates a named snapshot of the database."""
        snapshot_dir = os.path.join(storage_path, "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)
        # Ensure name is safe for filesystem
        safe_name = "".join(
            [c for c in name if c.isalnum() or c in (" ", ".", "-", "_")],
        ).strip()
        if not safe_name:
            safe_name = "unnamed_snapshot"

        snapshot_path = os.path.join(snapshot_dir, f"{safe_name}.zip")
        return self._backup_to_zip(snapshot_path)

    def list_snapshots(self, storage_path):
        """Lists all available snapshots."""
        snapshot_dir = os.path.join(storage_path, "snapshots")
        if not os.path.exists(snapshot_dir):
            return []

        snapshots = []
        for file in os.listdir(snapshot_dir):
            if file.endswith(".zip"):
                full_path = os.path.join(snapshot_dir, file)
                stats = os.stat(full_path)
                snapshots.append(
                    {
                        "name": file[:-4],
                        "path": full_path,
                        "size": stats.st_size,
                        "created_at": datetime.fromtimestamp(
                            stats.st_mtime,
                            UTC,
                        ).isoformat(),
                    },
                )
        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)

    def delete_snapshot_or_backup(
        self,
        storage_path,
        filename: str,
        is_backup: bool = False,
    ):
        """Deletes a database snapshot or auto-backup."""
        base_dir = "database-backups" if is_backup else "snapshots"
        file_path = os.path.join(storage_path, base_dir, filename)

        # Basic security check to ensure we stay within the intended directory
        abs_path = os.path.abspath(file_path)
        abs_base = os.path.abspath(os.path.join(storage_path, base_dir))

        if not abs_path.startswith(abs_base):
            msg = "Invalid path"
            raise ValueError(msg)

        if os.path.exists(abs_path):
            os.remove(abs_path)
            return True
        return False

    def restore_database(self, backup_path: str):
        if not os.path.exists(backup_path):
            msg = f"Backup not found at {backup_path}"
            raise FileNotFoundError(msg)

        paths = self._database_paths()
        self._checkpoint_and_close()

        # clean existing files
        for p in paths.values():
            if os.path.exists(p):
                os.remove(p)

        if zipfile.is_zipfile(backup_path):
            with zipfile.ZipFile(backup_path, "r") as zf:
                zf.extractall(os.path.dirname(paths["main"]))
        else:
            shutil.copy2(backup_path, paths["main"])

        # reopen and retune
        self.initialize()
        self._tune_sqlite_pragmas()
        integrity = self.provider.integrity_check()

        return {
            "restored_from": backup_path,
            "integrity_check": integrity,
        }
