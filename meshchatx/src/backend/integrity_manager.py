import os
import hashlib
import json
from pathlib import Path
from datetime import UTC, datetime


class IntegrityManager:
    """Manages the integrity of the database and identity files at rest."""

    def __init__(self, storage_dir, database_path, identity_hash=None):
        self.storage_dir = Path(storage_dir)
        self.database_path = Path(database_path)
        self.identity_hash = identity_hash
        self.manifest_path = self.storage_dir / "integrity-manifest.json"
        self.issues = []

    def _hash_file(self, file_path):
        if not os.path.exists(file_path):
            return None
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_integrity(self):
        """Verify the current state against the last saved manifest."""
        if not self.manifest_path.exists():
            return True, ["Initial run - no manifest yet"]

        try:
            with open(self.manifest_path, "r") as f:
                manifest = json.load(f)

            issues = []

            # Check Database
            db_rel = str(self.database_path.relative_to(self.storage_dir))
            actual_db_hash = self._hash_file(self.database_path)
            if actual_db_hash and actual_db_hash != manifest.get("files", {}).get(
                db_rel
            ):
                issues.append(f"Database modified: {db_rel}")

            # Check Identities and other critical files in storage_dir
            for root, _, files_in_dir in os.walk(self.storage_dir):
                for file in files_in_dir:
                    full_path = Path(root) / file
                    # Skip the manifest itself and temporary sqlite files
                    if (
                        file == "integrity-manifest.json"
                        or file.endswith("-wal")
                        or file.endswith("-shm")
                    ):
                        continue

                    rel_path = str(full_path.relative_to(self.storage_dir))
                    actual_hash = self._hash_file(full_path)

                    if rel_path in manifest.get("files", {}):
                        if actual_hash != manifest["files"][rel_path]:
                            issues.append(f"File modified: {rel_path}")
                    else:
                        # New files are also a concern for integrity
                        issues.append(f"New file detected: {rel_path}")

            if issues:
                m_date = manifest.get("date", "Unknown")
                m_time = manifest.get("time", "Unknown")
                m_id = manifest.get("identity", "Unknown")
                issues.insert(0, f"Last integrity snapshot: {m_date} {m_time} (Identity: {m_id})")

                # Check if identity matches
                if self.identity_hash and m_id != "Unknown" and self.identity_hash != m_id:
                    issues.append(f"Identity mismatch! Manifest belongs to: {m_id}")

            self.issues = issues
            return len(issues) == 0, issues
        except Exception as e:
            return False, [f"Integrity check failed: {str(e)}"]

    def save_manifest(self):
        """Snapshot the current state of critical files."""
        try:
            files = {}

            # Hash all critical files in storage_dir recursively
            for root, _, files_in_dir in os.walk(self.storage_dir):
                for file in files_in_dir:
                    full_path = Path(root) / file
                    # Skip the manifest itself and temporary sqlite files
                    if (
                        file == "integrity-manifest.json"
                        or file.endswith("-wal")
                        or file.endswith("-shm")
                    ):
                        continue

                    rel_path = str(full_path.relative_to(self.storage_dir))
                    files[rel_path] = self._hash_file(full_path)

            now = datetime.now(UTC)
            manifest = {
                "version": 1,
                "timestamp": now.timestamp(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "identity": self.identity_hash,
                "files": files,
            }

            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save integrity manifest: {e}")
            return False
