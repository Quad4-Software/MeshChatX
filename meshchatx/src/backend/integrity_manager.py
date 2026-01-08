import fnmatch
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


class IntegrityManager:
    """Manages the integrity of the database and identity files at rest."""

    # Files and directories that are frequently modified by RNS/LXMF or SQLite
    # and should be ignored during integrity checks.
    IGNORED_PATTERNS = [
        "*-wal",
        "*-shm",
        "*-journal",
        "*.tmp",
        "*.lock",
        "*.log",
        "*~",
        ".DS_Store",
        "Thumbs.db",
        "integrity-manifest.json",
    ]

    def __init__(self, storage_dir, database_path, identity_hash=None):
        self.storage_dir = Path(storage_dir)
        self.database_path = Path(database_path)
        self.identity_hash = identity_hash
        self.manifest_path = self.storage_dir / "integrity-manifest.json"
        self.issues = []

    def _should_ignore(self, rel_path):
        """Determine if a file path should be ignored based on name or directory."""
        path = Path(rel_path)
        path_parts = path.parts

        # Check for volatile LXMF/RNS directories
        # We only ignore these if they are inside the lxmf_router directory
        # to avoid accidentally ignoring important files with similar names.
        if "lxmf_router" in path_parts:
            if any(
                part in ["announces", "storage", "identities"] for part in path_parts
            ):
                return True

        # Check for other generally ignored directories
        if any(
            part in ["tmp", "recordings", "greetings", "docs", "bots", "ringtones"]
            for part in path_parts
        ):
            return True

        filename = path_parts[-1]

        # Check against IGNORED_PATTERNS
        if any(fnmatch.fnmatch(filename, pattern) for pattern in self.IGNORED_PATTERNS):
            return True

        return False

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
            with open(self.manifest_path) as f:
                manifest = json.load(f)

            issues = []
            manifest_files = manifest.get("files", {})

            # Check Database
            if self.database_path.exists():
                db_rel = str(self.database_path.relative_to(self.storage_dir))
                actual_db_hash = self._hash_file(self.database_path)
                if actual_db_hash and actual_db_hash != manifest_files.get(db_rel):
                    issues.append(f"Database modified: {db_rel}")

            # Check other critical files in storage_dir
            for root, _, files_in_dir in os.walk(self.storage_dir):
                for file in files_in_dir:
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.storage_dir))

                    if self._should_ignore(rel_path):
                        continue

                    # Database already checked separately, skip here to avoid double reporting
                    if full_path == self.database_path:
                        continue

                    actual_hash = self._hash_file(full_path)

                    if rel_path in manifest_files:
                        if actual_hash != manifest_files[rel_path]:
                            issues.append(f"File modified: {rel_path}")
                    else:
                        # New files are also a concern for integrity
                        # but we only report them if they are not in ignored dirs/patterns
                        issues.append(f"New file detected: {rel_path}")

            # Check for missing files that were in manifest
            for rel_path in manifest_files:
                if self._should_ignore(rel_path):
                    continue

                full_path = self.storage_dir / rel_path
                if not full_path.exists():
                    issues.append(f"File missing: {rel_path}")

            if issues:
                m_date = manifest.get("date", "Unknown")
                m_time = manifest.get("time", "Unknown")
                m_id = manifest.get("identity", "Unknown")
                issues.insert(
                    0,
                    f"Last integrity snapshot: {m_date} {m_time} (Identity: {m_id})",
                )

                # Check if identity matches
                if (
                    self.identity_hash
                    and m_id != "Unknown"
                    and self.identity_hash != m_id
                ):
                    issues.append(f"Identity mismatch! Manifest belongs to: {m_id}")

            self.issues = issues
            return len(issues) == 0, issues
        except Exception as e:
            import traceback

            traceback.print_exc()
            return False, [f"Integrity check failed: {e!s}"]

    def save_manifest(self):
        """Snapshot the current state of critical files."""
        try:
            files = {}

            # Hash all critical files in storage_dir recursively
            for root, _, files_in_dir in os.walk(self.storage_dir):
                for file in files_in_dir:
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.storage_dir))

                    if self._should_ignore(rel_path):
                        continue

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
