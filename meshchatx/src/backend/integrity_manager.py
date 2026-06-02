# SPDX-License-Identifier: 0BSD

import fnmatch
import hashlib
import json
import math
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar


class IntegrityManager:
    """Manages the integrity of the database and identity files at rest."""

    # Filename globs frequently rewritten by RNS/LXMF or SQLite that should be
    # ignored during integrity checks.
    IGNORED_PATTERNS: ClassVar[list[str]] = [
        "*-wal",
        "*-shm",
        "*-journal",
        "*.tmp",
        "*.lock",
        "*.log",
        "*~",
        "*.ratchets",
        ".DS_Store",
        "Thumbs.db",
        "integrity-manifest.json",
        "outbound_stamp_costs",
    ]

    # Any path containing one of these directory names is treated as volatile.
    # The whole lxmf_router tree (ratchets, message store, peer/announce
    # tables, delivery state) is rewritten continuously during normal
    # operation and must not be monitored, or it produces a constant stream of
    # false integrity warnings.
    VOLATILE_DIRS: ClassVar[set[str]] = {
        "lxmf_router",
        "ratchets",
        "messagestore",
        "tmp",
        "recordings",
        "greetings",
        "docs",
        "bots",
        "ringtones",
    }

    # Exact RNS/LXMF state filenames that change on their own during runtime.
    VOLATILE_FILENAMES: ClassVar[set[str]] = {
        "outbound_stamp_costs",
        "node_stats",
        "available_tickets",
        "local_deliveries",
        "locally_processed",
        "locally_delivered",
        "peers",
        "announce_cache",
        "destination_table",
        "announce_table",
        "known_destinations",
        "held_announces",
        "transport_identity",
        "identity_cache",
    }

    def __init__(self, storage_dir, database_path, identity_hash=None):
        self.storage_dir = Path(storage_dir)
        self.database_path = Path(database_path)
        self.identity_hash = identity_hash
        self.manifest_path = self.storage_dir / "integrity-manifest.json"
        self.issues = []

    def _should_ignore(self, rel_path):
        """Determine if a file path is volatile RNS/LXMF state to skip.

        Critical security components living directly under the identity storage
        directory (``identity``, ``config``, ``database.db``) are never ignored;
        only the continuously-rewritten LXMF router tree, ratchets, message
        store and known RNS state files are excluded.
        """
        path = Path(rel_path)
        path_parts = path.parts

        if any(part in self.VOLATILE_DIRS for part in path_parts):
            return True

        filename = path_parts[-1]

        if filename in self.VOLATILE_FILENAMES:
            return True

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

    def _calculate_entropy(self, file_path):
        """Calculate Shannon entropy of a file to detect content type shifts."""
        if not os.path.exists(file_path):
            return 0
        try:
            with open(file_path, "rb") as f:
                # Sample up to 64KB for performance
                data = f.read(65536)
            if not data:
                return 0

            byte_counts = [0] * 256
            for b in data:
                byte_counts[b] += 1

            entropy = 0
            total = len(data)
            for count in byte_counts:
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)
            return entropy
        except Exception:
            return 0

    def _check_db_integrity(self, db_path):
        """Use SQLite's PRAGMA integrity_check to verify the database."""
        if not os.path.exists(db_path):
            return False, "Database file does not exist"
        try:
            # Use read-only mode for checking
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            return result == "ok", result
        except Exception as e:
            return False, str(e)

    def check_integrity(self):
        """Verify the current state against the last saved manifest using advanced analytics."""
        if not self.manifest_path.exists():
            return True, ["Initial run - no manifest yet"]

        try:
            with open(self.manifest_path) as f:
                manifest = json.load(f)

            issues = []
            manifest_files = manifest.get("files", {})
            manifest_metadata = manifest.get("metadata", {})
            m_id = manifest.get("identity", "Unknown")

            # Always check for identity mismatch first as it's a fundamental security issue
            if self.identity_hash and m_id not in ("Unknown", self.identity_hash):
                issues.append(f"Identity mismatch! Manifest belongs to: {m_id}")

            # Check Database (Math-based structural check + Entropy stability + Hash)
            if self.database_path.exists():
                try:
                    db_rel = str(self.database_path.relative_to(self.storage_dir))
                except ValueError:
                    db_rel = str(self.database_path.name)
                actual_db_hash = self._hash_file(self.database_path)

                if actual_db_hash != manifest_files.get(db_rel):
                    is_db_ok, db_msg = self._check_db_integrity(self.database_path)
                    if not is_db_ok:
                        issues.append(f"Database structural issue: {db_msg}")
                    else:
                        actual_entropy = self._calculate_entropy(self.database_path)
                        saved_entropy = manifest_metadata.get(db_rel, {}).get("entropy")
                        if (
                            saved_entropy is not None
                            and abs(actual_entropy - saved_entropy) > 1.0
                        ):
                            issues.append(
                                f"Database structural anomaly (Entropy Δ: {abs(actual_entropy - saved_entropy):.2f})",
                            )

            # Check other critical files in storage_dir
            for root, _, files_in_dir in os.walk(self.storage_dir):
                for file in files_in_dir:
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.storage_dir))

                    if self._should_ignore(rel_path):
                        continue

                    # Database handled separately
                    if full_path == self.database_path:
                        continue

                    actual_hash = self._hash_file(full_path)

                    if rel_path in manifest_files:
                        if actual_hash != manifest_files[rel_path]:
                            actual_entropy = self._calculate_entropy(full_path)
                            saved_entropy = manifest_metadata.get(rel_path, {}).get(
                                "entropy",
                            )
                            saved_size = manifest_metadata.get(rel_path, {}).get(
                                "size",
                                0,
                            )
                            actual_size = full_path.stat().st_size

                            is_critical = any(
                                c in rel_path for c in ["identity", "config"]
                            )

                            if is_critical:
                                issues.append(
                                    f"Critical security component integrity compromised: {rel_path}",
                                )
                            elif (
                                saved_entropy is not None
                                and abs(actual_entropy - saved_entropy) > 1.5
                            ):
                                issues.append(
                                    f"Non-linear content shift detected in {rel_path} (Entropy Δ: {abs(actual_entropy - saved_entropy):.2f})",
                                )
                            elif saved_size and actual_size != saved_size:
                                issues.append(
                                    f"File size divergence: {rel_path} ({saved_size} -> {actual_size} bytes)",
                                )
                            else:
                                issues.append(f"File signature mismatch: {rel_path}")
                    else:
                        issues.append(f"New file detected: {rel_path}")

            # Check for missing files
            for rel_path in manifest_files:
                if self._should_ignore(rel_path):
                    continue

                full_path = self.storage_dir / rel_path
                if not full_path.exists():
                    issues.append(f"File missing: {rel_path}")

            if issues:
                m_date = manifest.get("date", "Unknown")
                m_time = manifest.get("time", "Unknown")
                issues.insert(
                    0,
                    f"Last integrity snapshot: {m_date} {m_time} (Identity: {m_id})",
                )

            self.issues = issues
            return len(issues) == 0, issues
        except Exception as e:
            return False, [f"Integrity check failed: {e!s}"]

    def save_manifest(self):
        """Snapshot the current state with extended mathematical metadata."""
        try:
            files = {}
            metadata = {}

            for root, _, files_in_dir in os.walk(self.storage_dir):
                for file in files_in_dir:
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.storage_dir))

                    if self._should_ignore(rel_path):
                        continue

                    files[rel_path] = self._hash_file(full_path)
                    metadata[rel_path] = {
                        "entropy": self._calculate_entropy(full_path),
                        "size": full_path.stat().st_size,
                    }

            now = datetime.now(UTC)
            manifest = {
                "version": 2,
                "timestamp": now.timestamp(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "identity": self.identity_hash,
                "files": files,
                "metadata": metadata,
            }

            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save integrity manifest: {e}")
            return False
