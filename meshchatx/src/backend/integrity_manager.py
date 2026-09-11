# SPDX-License-Identifier: 0BSD

import contextlib
import fnmatch
import hashlib
import hmac as hmac_mod
import json
import os
import secrets
import sqlite3
import stat as stat_mod
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from meshchatx.src.path_utils import atomic_write_text


class CriticalIntegrityError(RuntimeError):
    """Raised when tampering is detected in identity or database files at startup."""


def select_critical_integrity_issues(issues: list[str]) -> list[str]:
    return [
        issue
        for issue in issues
        if not issue.startswith(IntegrityManager.PENDING_PREFIX)
        and not issue.startswith(IntegrityManager.EXPECTED_PREFIX)
        and any(marker in issue for marker in IntegrityManager.CRITICAL_ISSUE_MARKERS)
    ]


class IntegrityManager:
    """Manages the integrity of the database and identity files at rest.

    Baselines are only refreshed at a clean shutdown or on explicit user
    acknowledge, never right after a check flagged issues, so findings are
    not silently blessed away. When the previous run did not shut down
    cleanly, drift in non-critical files is reported once as expected
    change instead of an alarm, while identity, database and manifest
    checks stay strict.

    The manifest is HMAC-signed with a key stored outside the monitored
    identity directory, and a signed registry records which identities
    have manifests, so deleting or swapping the manifest file no longer
    downgrades the check to a silent pass. This still cannot stop an
    attacker who controls the whole storage root; it detects offline
    tampering of a single identity tree, corruption, and restores of the
    wrong identity data.
    """

    CRITICAL_ISSUE_MARKERS: ClassVar[tuple[str, ...]] = (
        "Critical security component integrity compromised",
        "Database structural issue",
        "Identity mismatch",
    )

    PENDING_PREFIX: ClassVar[str] = "Previously reported: "
    EXPECTED_PREFIX: ClassVar[str] = "Expected change"

    MANIFEST_VERSION: ClassVar[int] = 3
    MANIFEST_NAME: ClassVar[str] = "integrity-manifest.json"
    REGISTRY_NAME: ClassVar[str] = "manifests.json"
    KEY_NAME: ClassVar[str] = "key"

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
        "*.mbtiles",
        ".DS_Store",
        "Thumbs.db",
        MANIFEST_NAME,
        "outbound_stamp_costs",
    ]

    # Any path containing one of these directory names is treated as volatile.
    # These trees are rewritten by the app, the user or remote peers during
    # normal operation; monitoring them produces a constant stream of false
    # integrity warnings.
    VOLATILE_DIRS: ClassVar[set[str]] = {
        "lxmf_router",
        "ratchets",
        "messagestore",
        "tmp",
        "recordings",
        "greetings",
        "voicemails",
        "ringtones",
        "notification_sounds",
        "docs",
        "meshchatx-docs",
        "reticulum-docs",
        "bots",
        "database-backups",
        "map_overlays",
        "map_data",
        "filesync",
        "repository-server",
        "rrc_hubs",
        "rrc_history",
        "rrc_server",
        "translation-packs",
        "page_nodes",
        "downloads",
        "rncp",
        "rncp_received",
        "rncp_shared",
    }

    # Exact state filenames that change on their own during runtime.
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
        "metadata.json",
        "rnx_sessions.json",
        "rnsh_sessions.json",
        "meshchatx_lxmf_address.txt",
        "meshchatx_bot_last_error.txt",
        "meshchatx_request_announce",
    }

    # Exact relative paths treated as critical security components. Anything
    # else that happens to contain "identity" or "config" in a directory or
    # file name is not allowed to block startup.
    CRITICAL_FILES: ClassVar[set[str]] = {
        "identity",
        "config",
        "database.db",
    }

    def __init__(
        self,
        storage_dir,
        database_path,
        identity_hash=None,
        trust_dir=None,
        app_version=None,
    ):
        self.storage_dir = Path(storage_dir)
        self.database_path = Path(database_path)
        self.identity_hash = identity_hash
        self.trust_dir = Path(trust_dir) if trust_dir else None
        self.app_version = app_version
        self.manifest_path = self.storage_dir / self.MANIFEST_NAME
        self.issues = []
        self._lenient = False
        # True when no manifest existed at the last check, meaning the
        # baseline still has to be established.
        self.baseline_pending = False

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------

    def _should_ignore(self, rel_path):
        """Determine if a file path is volatile state to skip.

        The identity file, config and database living directly under the
        identity storage directory are never ignored; only continuously
        rewritten app and user content trees are excluded.
        """
        path = Path(rel_path)
        path_parts = path.parts

        if any(part in self.VOLATILE_DIRS for part in path_parts):
            return True

        # Restore staging/aside leftovers are app artifacts, not tampering.
        if any(part.startswith(".meshchatx-") for part in path_parts):
            return True

        filename = path_parts[-1]

        if filename in self.VOLATILE_FILENAMES:
            return True

        if any(fnmatch.fnmatch(filename, pattern) for pattern in self.IGNORED_PATTERNS):
            return True

        return False

    def _is_critical_path(self, rel_path):
        """Critical files are exact names at the storage root or top level."""
        parts = Path(rel_path).parts
        return len(parts) == 1 and parts[0] in self.CRITICAL_FILES

    @staticmethod
    def _valid_rel_path(rel_path):
        """Manifest paths must stay inside the storage dir."""
        parts = Path(rel_path).parts
        return not Path(rel_path).is_absolute() and ".." not in parts

    # ------------------------------------------------------------------
    # Hashing and scanning
    # ------------------------------------------------------------------

    def _hash_file(self, file_path):
        try:
            if not stat_mod.S_ISREG(os.stat(file_path).st_mode):
                return None
        except OSError:
            return None
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _stat_signature(self, file_path):
        try:
            st = os.stat(file_path)
        except OSError:
            return None
        if not stat_mod.S_ISREG(st.st_mode):
            # Fifos, sockets and devices can block or stream forever on
            # open; only regular files are hashed.
            return None
        return {"size": st.st_size, "mtime_ns": st.st_mtime_ns}

    def _scan_storage(self):
        """Walk the storage dir once, returning {rel: {sha256,size,mtime_ns}}.

        Symlinks are skipped so a planted link cannot point the scan at files
        outside the identity jail.
        """
        entries = {}
        for root, dirs, files_in_dir in os.walk(self.storage_dir):
            dirs[:] = [
                d
                for d in dirs
                if d not in self.VOLATILE_DIRS and not (Path(root) / d).is_symlink()
            ]
            for file in files_in_dir:
                full_path = Path(root) / file
                if full_path.is_symlink():
                    continue
                rel_path = str(full_path.relative_to(self.storage_dir))
                if self._should_ignore(rel_path):
                    continue
                sig = self._stat_signature(full_path)
                if sig is None:
                    continue
                digest = self._hash_file(full_path)
                if digest is None:
                    continue
                # File rewritten while hashing; skip it so the baseline never
                # stores a torn read. The next snapshot catches it.
                if self._stat_signature(full_path) != sig:
                    continue
                entries[rel_path] = {"sha256": digest, **sig}
        return entries

    def _check_db_integrity(self, db_path):
        """Use SQLite's PRAGMA integrity_check to verify the database."""
        if not os.path.exists(db_path):
            return False, "Database file does not exist"
        try:
            # Use read-only mode for checking
            with contextlib.closing(
                sqlite3.connect(f"file:{db_path}?mode=ro", uri=True),
            ) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            return result == "ok", result
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # Manifest authenticity
    # ------------------------------------------------------------------

    def _key_path(self):
        return self.trust_dir / self.KEY_NAME if self.trust_dir else None

    def _registry_path(self):
        return self.trust_dir / self.REGISTRY_NAME if self.trust_dir else None

    def _load_key(self, create=False):
        key_path = self._key_path()
        if key_path is None:
            return None
        try:
            if key_path.exists():
                key = key_path.read_bytes()
                return key or None
            if not create:
                return None
            key = secrets.token_bytes(32)
            self.trust_dir.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(
                    key_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                # Another context won the create race; use its key.
                existing = key_path.read_bytes()
                return existing or None
            with os.fdopen(fd, "wb") as f:
                f.write(key)
            return key
        except OSError:
            return None

    @staticmethod
    def _canonical(payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _sign_payload(self, key, payload):
        return hmac_mod.new(
            key,
            self._canonical(payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _manifest_hmac(self, key, manifest):
        body = {k: v for k, v in manifest.items() if k != "hmac"}
        return self._sign_payload(key, body)

    def _load_registry(self, key):
        """Return (entries, status). status: ok | missing | tampered."""
        registry_path = self._registry_path()
        if registry_path is None or not registry_path.exists():
            return {}, "missing"
        try:
            data = json.loads(registry_path.read_text())
            entries = data.get("identities", {})
            if not isinstance(entries, dict):
                return {}, "tampered"
            expected = data.get("hmac")
            if key is not None and expected is not None:
                actual = self._sign_payload(key, {"identities": entries})
                if not hmac_mod.compare_digest(actual, expected):
                    return {}, "tampered"
            return entries, "ok"
        except Exception:
            return {}, "tampered"

    def _save_registry(self, key, entries):
        registry_path = self._registry_path()
        if registry_path is None:
            return
        payload = {"identities": entries}
        payload["hmac"] = self._sign_payload(key, payload)
        try:
            self.trust_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(registry_path, json.dumps(payload, indent=2))
        except OSError:
            pass

    def _other_manifests_on_disk(self):
        identities_dir = self.storage_dir.parent
        try:
            return any(
                child.is_dir() and (child / self.MANIFEST_NAME).exists()
                for child in identities_dir.iterdir()
            )
        except OSError:
            return False

    def _verify_manifest_auth(self, manifest, issues, key):
        """Check manifest signature and registry. Returns issues found."""
        registry_entries, registry_status = self._load_registry(key)
        has_registry_entry = self.identity_hash in registry_entries

        if registry_status == "tampered":
            issues.append("Integrity registry signature mismatch")

        if manifest is None:
            if has_registry_entry:
                issues.append(
                    "Critical security component integrity compromised: "
                    "Integrity manifest removed",
                )
            elif (
                registry_status == "missing"
                and key is not None
                and self._other_manifests_on_disk()
            ):
                issues.append(
                    "Integrity registry removed while manifests exist on disk",
                )
            return issues

        stored_hmac = manifest.get("hmac")
        if stored_hmac is None:
            if key is not None:
                # Signing was already initialized on this install, so an
                # unsigned manifest is a downgrade, not a legacy upgrade.
                issues.append(
                    "Integrity manifest unsigned on a signed install",
                )
        elif key is None:
            issues.append(
                "Integrity trust key missing; manifest signature unverified",
            )
        else:
            actual = self._manifest_hmac(key, manifest)
            if not hmac_mod.compare_digest(actual, stored_hmac):
                issues.append(
                    "Critical security component integrity compromised: "
                    "Integrity manifest tampered or replaced",
                )

        if (
            registry_status == "missing"
            and key is not None
            and self._other_manifests_on_disk()
        ):
            issues.append("Integrity registry missing while manifests exist")

        return issues

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    def check_integrity(self, critical_only: bool = False, live: bool = False):
        """Verify the current state against the last saved manifest.

        critical_only limits the scan to identity, config and database files
        for the fast startup path. live skips the database file contents
        because it is open and being rewritten while the app runs.
        """
        self.baseline_pending = not self.manifest_path.exists()
        if self.baseline_pending:
            if self.trust_dir is not None:
                key = self._load_key()
                issues = self._verify_manifest_auth(None, [], key)
                if issues:
                    self.issues = issues
                    return False, issues
            return True, ["Initial run - no manifest yet"]

        try:
            with open(self.manifest_path) as f:
                manifest = json.load(f)
        except Exception as e:
            self.issues = [f"Integrity check failed: {e!s}"]
            return False, self.issues

        try:
            issues = []
            key = self._load_key()
            self._verify_manifest_auth(manifest, issues, key)

            manifest_files = manifest.get("files", {})
            if not isinstance(manifest_files, dict):
                manifest_files = {}
            manifest_metadata = manifest.get("metadata", {})
            if not isinstance(manifest_metadata, dict):
                manifest_metadata = {}
            m_id = manifest.get("identity", "Unknown")

            # Drift is expected after an unclean shutdown or an app update:
            # files the app was writing when it died legitimately differ from
            # the last snapshot. Demote those diffs to expected-change notes;
            # identity, database and manifest checks stay strict.
            clean_exit = manifest.get("clean_exit", True)
            version_changed = (
                self.app_version
                and manifest.get("app_version")
                and manifest["app_version"] != self.app_version
            )
            self._lenient = not clean_exit or bool(version_changed)

            pending = manifest.get("pending_issues", [])
            if not isinstance(pending, list):
                pending = []
            issues.extend(f"{self.PENDING_PREFIX}{issue}" for issue in pending)

            if self.identity_hash and m_id not in ("Unknown", self.identity_hash):
                issues.append(f"Identity mismatch! Manifest belongs to: {m_id}")

            self._check_database(manifest_files, issues, live=live)

            if critical_only:
                self._check_critical_files(manifest_files, issues)
            else:
                self._check_tree(manifest_files, manifest_metadata, issues)

            if issues:
                m_date = manifest.get("date", "Unknown")
                m_time = manifest.get("time", "Unknown")
                issues.insert(
                    0,
                    f"Last integrity snapshot: {m_date} {m_time} (Identity: {m_id})",
                )

            # Findings accumulate across boot and deferred checks so pending
            # issues saved at shutdown reflect everything seen this run.
            fresh = {
                issue
                for issue in issues
                if not issue.startswith(self.EXPECTED_PREFIX)
                and "Last integrity snapshot" not in issue
            }
            self.issues = sorted(set(self.issues) | fresh)
            return len(issues) == 0, issues
        except Exception as e:
            return False, [f"Integrity check failed: {e!s}"]

    def _report_drift(self, rel_path, kind, issues):
        """Report a changed/missing/new file.

        Demotes to an expected-change note when the baseline was not a
        clean shutdown snapshot.
        """
        if self._lenient and not self._is_critical_path(rel_path):
            issues.append(
                f"{self.EXPECTED_PREFIX} after unclean shutdown or update: "
                f"{kind}: {rel_path}",
            )
        elif kind == "modified":
            issues.append(f"File signature mismatch: {rel_path}")
        elif kind == "missing":
            issues.append(f"File missing: {rel_path}")
        else:
            issues.append(f"New file detected: {rel_path}")

    def _check_database(self, manifest_files, issues, live):
        if not self.database_path.exists():
            issues.append(
                "Critical security component integrity compromised: "
                "database.db missing",
            )
            return
        try:
            if not stat_mod.S_ISREG(os.stat(self.database_path).st_mode):
                issues.append(
                    "Critical security component integrity compromised: "
                    "database.db is not a regular file",
                )
                return
        except OSError:
            return
        if live:
            return
        try:
            db_rel = str(self.database_path.relative_to(self.storage_dir))
        except ValueError:
            db_rel = str(self.database_path.name)
        actual_db_hash = self._hash_file(self.database_path)

        if actual_db_hash == manifest_files.get(db_rel):
            return

        is_db_ok, db_msg = self._check_db_integrity(self.database_path)
        if not is_db_ok:
            issues.append(f"Database structural issue: {db_msg}")
        elif self._lenient:
            issues.append(
                f"{self.EXPECTED_PREFIX} after unclean shutdown or update: "
                "modified: database.db",
            )
        else:
            issues.append(
                "File signature mismatch: database.db "
                "(database changed outside normal operation)",
            )

    def _check_critical_files(self, manifest_files, issues):
        for rel_path, expected_hash in manifest_files.items():
            if not self._valid_rel_path(rel_path):
                continue
            if self._should_ignore(rel_path) or not self._is_critical_path(rel_path):
                continue
            if rel_path == self._db_rel_path():
                continue
            full_path = self.storage_dir / rel_path
            sig = self._stat_signature(full_path)
            if sig is None:
                issues.append(
                    "Critical security component integrity "
                    f"compromised: {rel_path} missing",
                )
                continue
            actual_hash = self._hash_file(full_path)
            if self._stat_signature(full_path) != sig:
                continue  # mid-write; the next check catches it
            if actual_hash != expected_hash:
                issues.append(
                    f"Critical security component integrity compromised: {rel_path}",
                )

    def _db_rel_path(self):
        try:
            return str(self.database_path.relative_to(self.storage_dir))
        except ValueError:
            return str(self.database_path.name)

    def _check_tree(self, manifest_files, manifest_metadata, issues):
        for root, dirs, files_in_dir in os.walk(self.storage_dir):
            dirs[:] = [
                d
                for d in dirs
                if d not in self.VOLATILE_DIRS and not (Path(root) / d).is_symlink()
            ]
            for file in files_in_dir:
                full_path = Path(root) / file
                if full_path.is_symlink():
                    continue
                rel_path = str(full_path.relative_to(self.storage_dir))

                if self._should_ignore(rel_path):
                    continue

                # Database handled separately
                if full_path == self.database_path:
                    continue

                expected_hash = manifest_files.get(rel_path)
                if expected_hash is None:
                    if self._is_critical_path(rel_path):
                        issues.append(
                            "Critical security component integrity "
                            f"compromised: {rel_path} appeared",
                        )
                    else:
                        self._report_drift(rel_path, "new", issues)
                    continue

                saved_meta = manifest_metadata.get(rel_path, {})
                if not isinstance(saved_meta, dict):
                    saved_meta = {}
                sig = self._stat_signature(full_path)
                if sig is None:
                    continue  # vanished mid-scan; the missing pass reports it
                if (
                    saved_meta.get("size") == sig["size"]
                    and saved_meta.get("mtime_ns") == sig["mtime_ns"]
                ):
                    continue

                actual_hash = self._hash_file(full_path)
                if self._stat_signature(full_path) != sig:
                    continue  # mid-write; the next check catches it
                if actual_hash != expected_hash:
                    if self._is_critical_path(rel_path):
                        issues.append(
                            "Critical security component integrity "
                            f"compromised: {rel_path}",
                        )
                    else:
                        self._report_drift(rel_path, "modified", issues)

        db_rel = self._db_rel_path()
        for rel_path in manifest_files:
            if not self._valid_rel_path(rel_path):
                continue
            if self._should_ignore(rel_path):
                continue
            if rel_path == db_rel:
                continue
            if not (self.storage_dir / rel_path).exists():
                if self._is_critical_path(rel_path):
                    issues.append(
                        "Critical security component integrity "
                        f"compromised: {rel_path} missing",
                    )
                else:
                    self._report_drift(rel_path, "missing", issues)

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    def save_manifest(self, reason: str = "shutdown"):
        """Snapshot the current state.

        reason is "shutdown" for a clean exit snapshot, "acknowledge" when
        the user accepts current state, or "initial" for a first baseline.
        Unacknowledged issues carry forward so they resurface until the
        user explicitly acknowledges them.
        """
        try:
            scanned = self._scan_storage()
            files = {rel: entry["sha256"] for rel, entry in scanned.items()}
            metadata = {
                rel: {"size": entry["size"], "mtime_ns": entry["mtime_ns"]}
                for rel, entry in scanned.items()
            }

            now = datetime.now(UTC)
            manifest = {
                "version": self.MANIFEST_VERSION,
                "timestamp": now.timestamp(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "identity": self.identity_hash,
                "app_version": self.app_version,
                "clean_exit": reason == "shutdown",
                "pending_issues": []
                if reason == "acknowledge"
                else [
                    issue[len(self.PENDING_PREFIX) :]
                    if issue.startswith(self.PENDING_PREFIX)
                    else issue
                    for issue in self.issues
                ],
                "files": files,
                "metadata": metadata,
            }

            key = self._load_key(create=True)
            if key is not None:
                manifest["hmac"] = self._manifest_hmac(key, manifest)

            atomic_write_text(self.manifest_path, json.dumps(manifest, indent=2))
            self.baseline_pending = False

            if key is not None and self.identity_hash:
                entries, status = self._load_registry(key)
                if status == "tampered":
                    entries = {}
                entries[self.identity_hash] = {"updated": now.isoformat()}
                self._save_registry(key, entries)

            if reason == "acknowledge":
                self.issues = []
            return True
        except Exception as e:
            print(f"Failed to save integrity manifest: {e}")
            return False

    def clear_baseline(self):
        """Delete the manifest and drop this identity's registry entry.

        Used after a database restore replaces the whole identity tree: the
        old baseline describes files that no longer exist, so the next run
        must build a fresh one instead of flagging the restore.
        """
        with contextlib.suppress(OSError):
            self.manifest_path.unlink(missing_ok=True)
        key = self._load_key()
        if key is not None and self.identity_hash:
            entries, status = self._load_registry(key)
            if status != "tampered" and self.identity_hash in entries:
                del entries[self.identity_hash]
                self._save_registry(key, entries)
        self.baseline_pending = True
