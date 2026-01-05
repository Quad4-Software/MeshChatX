import os
import shutil
import zipfile
from datetime import UTC, datetime

from .announces import AnnounceDAO
from .config import ConfigDAO
from .contacts import ContactsDAO
from .debug_logs import DebugLogsDAO
from .legacy_migrator import LegacyMigrator
from .map_drawings import MapDrawingsDAO
from .messages import MessageDAO
from .misc import MiscDAO
from .provider import DatabaseProvider
from .ringtones import RingtoneDAO
from .schema import DatabaseSchema
from .telemetry import TelemetryDAO
from .telephone import TelephoneDAO
from .voicemails import VoicemailDAO


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
        self.debug_logs = DebugLogsDAO(self.provider)

    def initialize(self):
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
            self.execute_sql("PRAGMA wal_autocheckpoint=1000")
            self.execute_sql("PRAGMA temp_store=MEMORY")
            self.execute_sql("PRAGMA journal_mode=WAL")
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
        free_bytes = (
            page_size * freelist_pages if page_size > 0 and freelist_pages > 0 else 0
        )

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

    def backup_database(self, storage_path, backup_path: str | None = None):
        default_dir = os.path.join(storage_path, "database-backups")
        os.makedirs(default_dir, exist_ok=True)
        if backup_path is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            backup_path = os.path.join(default_dir, f"backup-{timestamp}.zip")

        return self._backup_to_zip(backup_path)

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
