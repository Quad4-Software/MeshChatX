# SPDX-License-Identifier: 0BSD

"""Extra integrity edge cases for critical-only startup checks."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from meshchatx.src.backend.integrity_manager import (
    IntegrityManager,
    select_critical_integrity_issues,
)


class TestCriticalOnlyIntegrity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "database.db"
        self.db_path.write_bytes(b"db-bytes")
        self.identity_path = Path(self.test_dir) / "identity"
        self.identity_path.write_bytes(b"identity-bytes")
        self.manager = IntegrityManager(
            self.test_dir,
            str(self.db_path),
            identity_hash="hash-a",
        )
        self.manager.save_manifest()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_critical_only_passes_unchanged_tree(self):
        is_ok, issues = self.manager.check_integrity(critical_only=True)
        self.assertTrue(is_ok)
        self.assertEqual(select_critical_integrity_issues(issues), [])

    def test_critical_only_detects_missing_identity(self):
        self.identity_path.unlink()
        is_ok, issues = self.manager.check_integrity(critical_only=True)
        self.assertFalse(is_ok)
        self.assertTrue(
            select_critical_integrity_issues(issues)
            or any("missing" in i.lower() for i in issues)
        )

    def test_critical_only_skips_non_critical_size_drift(self):
        notes = Path(self.test_dir) / "notes.bin"
        notes.write_bytes(b"aaaa")
        self.manager.save_manifest()
        notes.write_bytes(b"bbbbbbbb")
        is_ok_critical, issues_critical = self.manager.check_integrity(
            critical_only=True
        )
        self.assertTrue(
            is_ok_critical or not select_critical_integrity_issues(issues_critical),
        )
        is_ok_full, issues_full = self.manager.check_integrity(critical_only=False)
        self.assertFalse(is_ok_full)
        self.assertTrue(any("notes.bin" in issue for issue in issues_full))

    def test_select_critical_markers_cover_identity_and_db(self):
        issues = [
            "File signature mismatch: notes.bin",
            "Critical security component integrity compromised: identity",
            "Database structural issue: corrupt",
            "Identity mismatch! Manifest belongs to: other",
        ]
        critical = select_critical_integrity_issues(issues)
        self.assertEqual(len(critical), 3)
        self.assertNotIn("File signature mismatch: notes.bin", critical)
