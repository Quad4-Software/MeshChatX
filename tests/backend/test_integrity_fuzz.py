# SPDX-License-Identifier: 0BSD

"""Property and fuzz tests for IntegrityManager with explicit oracles.

Every test predicts accept/reject from the input alone: volatile paths must
never produce findings, monitored non-critical paths must surface drift in
exactly one message class, and critical paths must always produce a critical
marker regardless of lenient mode.
"""

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.integrity_manager import (
    IntegrityManager,
    select_critical_integrity_issues,
)

VOLATILE_DIR_NAMES = sorted(IntegrityManager.VOLATILE_DIRS)
VOLATILE_FILE_NAMES = sorted(IntegrityManager.VOLATILE_FILENAMES)
NORMAL_DIRS = ["data", "misc", "custom"]
NORMAL_FILES = ["notes.txt", "payload.bin", "extra.json", "blob"]
CRITICAL_FILES = sorted(IntegrityManager.CRITICAL_FILES - {"database.db"})


def _rel_path_strategy():
    """Relative paths mixing volatile and monitored locations."""
    volatile_dir = st.sampled_from(VOLATILE_DIR_NAMES)
    normal_dir = st.sampled_from(NORMAL_DIRS)
    volatile_file = st.sampled_from(VOLATILE_FILE_NAMES)
    normal_file = st.sampled_from(NORMAL_FILES)
    critical_file = st.sampled_from(CRITICAL_FILES)
    return st.one_of(
        normal_file,
        critical_file,
        st.builds(lambda d, f: f"{d}/{f}", volatile_dir, normal_file),
        st.builds(lambda d, f: f"{d}/{f}", normal_dir, normal_file),
        st.builds(lambda d, f: f"{d}/{f}", normal_dir, volatile_file),
    )


def _file_tree_strategy():
    """A dict of rel_path -> bytes for a small random storage tree."""
    return st.dictionaries(
        _rel_path_strategy(),
        st.binary(min_size=1, max_size=128),
        min_size=1,
        max_size=8,
    )


def _expected_classification(rel_path):
    """Oracle: what class a mutated path falls into."""
    if IntegrityManager("", "/nonexistent")._should_ignore(rel_path):
        return "ignored"
    parts = Path(rel_path).parts
    if len(parts) == 1 and parts[0] in IntegrityManager.CRITICAL_FILES:
        return "critical"
    return "monitored"


class IntegrityFuzzBase(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "database.db"
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.close()
        self.manager = IntegrityManager(self.test_dir, self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_tree(self, tree):
        for rel, data in tree.items():
            path = self.test_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


class TestIntegrityFuzz(IntegrityFuzzBase):
    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=30,
        derandomize=True,
    )
    @given(tree=_file_tree_strategy())
    def test_save_then_check_always_clean(self, tree):
        """Oracle: a snapshot taken and immediately checked reports nothing."""
        self._write_tree(tree)
        self.assertTrue(self.manager.save_manifest())
        is_ok, issues = self.manager.check_integrity()
        self.assertTrue(is_ok, f"unchanged tree flagged: {issues}")

    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=30,
        derandomize=True,
    )
    @given(
        tree=_file_tree_strategy(),
        target=_rel_path_strategy(),
        new_data=st.binary(min_size=1, max_size=128),
    )
    def test_single_mutation_classification(self, tree, target, new_data):
        """Oracle: mutating a file must be classified by its scope."""
        self._write_tree(tree)
        self.manager.save_manifest()

        path = self.test_dir / target
        path.parent.mkdir(parents=True, exist_ok=True)
        old_data = path.read_bytes() if path.exists() else None
        if old_data == new_data:
            new_data = new_data + b"x"
        path.write_bytes(new_data)

        is_ok, issues = self.manager.check_integrity()
        classification = _expected_classification(target)
        if classification == "ignored":
            self.assertTrue(
                is_ok or all(target not in i for i in issues),
                f"volatile path {target} flagged: {issues}",
            )
        elif classification == "critical":
            self.assertTrue(
                select_critical_integrity_issues(issues),
                f"critical path {target} did not produce a marker: {issues}",
            )
        else:
            self.assertTrue(
                any(target in i for i in issues),
                f"monitored path {target} produced no finding: {issues}",
            )

    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=30,
        derandomize=True,
    )
    @given(tree=_file_tree_strategy(), target=_rel_path_strategy())
    def test_single_deletion_classification(self, tree, target):
        """Oracle: deleting a file must be classified by its scope."""
        self._write_tree(tree)
        path = self.test_dir / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"victim")
        self.manager.save_manifest()
        path.unlink()

        is_ok, issues = self.manager.check_integrity()
        classification = _expected_classification(target)
        if classification == "ignored":
            self.assertTrue(
                is_ok or all(target not in i for i in issues),
                f"volatile path {target} flagged: {issues}",
            )
        elif classification == "critical":
            self.assertTrue(
                select_critical_integrity_issues(issues),
                f"critical delete {target} not critical: {issues}",
            )
        else:
            self.assertTrue(
                any(target in i for i in issues),
                f"monitored delete {target} produced no finding: {issues}",
            )

    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=25,
        derandomize=True,
    )
    @given(manifest_bytes=st.binary(min_size=0, max_size=512))
    def test_manifest_bytes_never_crash(self, manifest_bytes):
        """Oracle: any manifest content yields (bool, list[str]) or a safe failure."""
        self.manager.manifest_path.write_bytes(manifest_bytes)
        is_ok, issues = self.manager.check_integrity()
        self.assertIsInstance(is_ok, bool)
        self.assertTrue(all(isinstance(i, str) for i in issues))

    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=25,
        derandomize=True,
    )
    @given(
        manifest=st.fixed_dictionaries(
            {},
            optional={
                "version": st.integers(),
                "identity": st.one_of(st.text(), st.none(), st.integers()),
                "clean_exit": st.booleans(),
                "app_version": st.one_of(st.text(), st.none()),
                "pending_issues": st.one_of(
                    st.lists(st.text(), max_size=4),
                    st.text(),
                    st.integers(),
                ),
                "files": st.dictionaries(st.text(), st.text(), max_size=4),
                "metadata": st.dictionaries(
                    st.text(),
                    st.dictionaries(st.text(), st.integers(), max_size=3),
                    max_size=4,
                ),
                "hmac": st.text(),
            },
        ),
    )
    def test_manifest_shape_fuzz(self, manifest):
        """Oracle: structurally valid JSON with hostile shapes never crashes."""
        self.manager.manifest_path.write_text(json.dumps(manifest))
        is_ok, issues = self.manager.check_integrity()
        self.assertIsInstance(is_ok, bool)
        self.assertTrue(all(isinstance(i, str) for i in issues))

    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=25,
        derandomize=True,
    )
    @given(
        tree=_file_tree_strategy(),
        target=_rel_path_strategy(),
        new_data=st.binary(min_size=1, max_size=64),
    )
    def test_lenient_mode_classification(self, tree, target, new_data):
        """Demote non-critical drift after unclean shutdown only.

        Oracle: after unclean shutdown, non-critical drift demotes while
        critical drift stays critical.
        """
        self._write_tree(tree)
        self.manager.save_manifest(reason="initial")

        path = self.test_dir / target
        path.parent.mkdir(parents=True, exist_ok=True)
        old_data = path.read_bytes() if path.is_file() else None
        if old_data == new_data:
            new_data = new_data + b"x"
        path.write_bytes(new_data)

        _is_ok, issues = self.manager.check_integrity()
        classification = _expected_classification(target)
        if classification == "ignored":
            self.assertTrue(all(target not in i for i in issues))
        elif classification == "critical":
            self.assertTrue(
                select_critical_integrity_issues(issues),
                f"critical {target} demoted under lenient mode: {issues}",
            )
        else:
            matching = [i for i in issues if target in i]
            self.assertTrue(matching, f"no finding for {target}: {issues}")
            self.assertTrue(
                all("Expected change" in i for i in matching),
                f"non-critical {target} not demoted: {matching}",
            )


class TestIntegrityTrustFuzz(unittest.TestCase):
    """Fuzz the signed-manifest trust path."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.trust_dir = self.test_dir / "trust"
        self.storage = self.test_dir / "identities" / "id1"
        self.storage.mkdir(parents=True)
        self.db_path = self.storage / "database.db"
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.close()
        (self.storage / "identity").write_bytes(b"key")
        self.manager = IntegrityManager(
            self.storage,
            self.db_path,
            identity_hash="id1",
            trust_dir=self.trust_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @settings(
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
        deadline=None,
        max_examples=25,
        derandomize=True,
    )
    @given(
        corruption=st.one_of(
            st.binary(min_size=1, max_size=256),
            st.text(),
            st.binary(min_size=1, max_size=16).map(
                lambda b: json.dumps({"files": {"x": b.hex()}}),
            ),
        ),
    )
    def test_signed_manifest_corruption_detected(self, corruption):
        """Detect byte-level rewrites of a signed manifest.

        Oracle: the rewrite must fail signature or JSON parsing; it must
        never pass silently.
        """
        self.manager.save_manifest()
        original = self.manager.manifest_path.read_bytes()
        payload = corruption.encode() if isinstance(corruption, str) else corruption
        self.manager.manifest_path.write_bytes(payload)
        corruption = payload

        is_ok, issues = self.manager.check_integrity()
        if corruption == original:
            self.assertTrue(is_ok)
            return
        try:
            loaded = json.loads(corruption)
        except Exception:
            loaded = None
        if isinstance(loaded, dict) and loaded == json.loads(original):
            self.assertTrue(is_ok)
            return
        self.assertFalse(is_ok, "corrupted signed manifest passed")
        self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
