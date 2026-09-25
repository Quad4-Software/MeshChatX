# SPDX-License-Identifier: 0BSD

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import RNS

from meshchatx.src.backend.recovery.crash_recovery import CrashRecovery


class TestCrashRecovery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.test_dir, "storage")
        os.makedirs(self.storage_dir)
        self.db_path = os.path.join(self.storage_dir, "test.db")
        self.public_dir = os.path.join(self.test_dir, "public")
        os.makedirs(self.public_dir)
        with open(os.path.join(self.public_dir, "index.html"), "w") as f:
            f.write("test")

        self.recovery = CrashRecovery(
            storage_dir=self.storage_dir,
            database_path=self.db_path,
            public_dir=self.public_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_diagnosis_normal(self):
        # Create a valid DB
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.close()

        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()

        self.assertIn("OS:", report)
        self.assertIn("Python:", report)
        self.assertIn("Storage Path:", report)
        self.assertIn("Integrity: OK", report)
        self.assertIn("Frontend Status: Assets verified", report)

    def test_diagnosis_missing_storage(self):
        shutil.rmtree(self.storage_dir)
        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("[ERROR] Storage path does not exist", report)

    def test_diagnosis_corrupt_db(self):
        with open(self.db_path, "w") as f:
            f.write("not a sqlite database")

        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("[ERROR] Database is unreadable", report)

    def test_diagnosis_missing_frontend(self):
        shutil.rmtree(self.public_dir)
        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("[ERROR] Frontend directory is missing", report)

    def test_diagnosis_rns_missing_config(self):
        rns_dir = os.path.join(self.test_dir, "rns_missing")
        self.recovery.update_paths(reticulum_config_dir=rns_dir)
        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("[ERROR] Reticulum config directory does not exist", report)

    def test_reticulum_diagnosis_skips_false_missing_when_path_unset(self):
        with patch.object(RNS.Reticulum, "configpath", ""):
            self.recovery.update_paths(reticulum_config_dir=None)
            output = io.StringIO()
            self.recovery.run_reticulum_diagnosis(file=output)
            report = output.getvalue()
            self.assertIn("(not resolved yet)", report)
            self.assertNotIn(
                "[ERROR] Reticulum config directory does not exist",
                report,
            )

    def test_diagnosis_rns_log_extraction(self):
        rns_dir = os.path.join(self.test_dir, "rns_log")
        os.makedirs(rns_dir)
        log_file = os.path.join(rns_dir, "logfile")
        with open(log_file, "w") as f:
            f.write("Line 1\nLine 2\nERROR: Something went wrong\n")

        self.recovery.update_paths(reticulum_config_dir=rns_dir)
        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("Recent Log Entries", report)
        self.assertIn("> [ALERT] ERROR: Something went wrong", report)

    def test_env_disable(self):
        os.environ["MESHCHAT_NO_CRASH_RECOVERY"] = "1"
        recovery = CrashRecovery()
        self.assertFalse(recovery.enabled)
        del os.environ["MESHCHAT_NO_CRASH_RECOVERY"]

    def test_handle_exception_format(self):
        # We don't want to actually sys.exit(1) in tests, so we mock it
        original_exit = sys.exit
        sys.exit = lambda x: None

        output = io.StringIO()
        # Redirect stderr to our buffer
        original_stderr = sys.stderr
        sys.stderr = output

        try:
            try:
                raise ValueError("Simulated error for testing")
            except ValueError:
                self.recovery.handle_exception(*sys.exc_info())
        finally:
            sys.stderr = original_stderr
            sys.exit = original_exit

        report = output.getvalue()
        self.assertIn("!!! APPLICATION CRASH DETECTED !!!", report)
        self.assertIn("Type:    ValueError", report)
        self.assertIn("Message: Simulated error for testing", report)
        self.assertIn("Root Cause Analysis:", report)
        self.assertIn("Recovery Suggestions:", report)

    def test_heuristic_analysis_sqlite(self):
        exc_type = type("OperationalError", (Exception,), {})
        exc_type.__name__ = "sqlite3.OperationalError"
        exc_value = Exception("no such table: config")
        diagnosis = {"db_type": "memory"}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertTrue(len(causes) > 0)
        self.assertEqual(causes[0]["description"], "In-Memory Database Sync Failure")

    def test_heuristic_analysis_asyncio(self):
        exc_type = RuntimeError
        exc_value = RuntimeError("no current event loop")
        diagnosis = {}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertTrue(len(causes) > 0)
        self.assertIn("Asynchronous Initialization", causes[0]["description"])

    def test_heuristic_analysis_oom_priority(self):
        """Verify that low memory increases OOM score even with other errors."""
        exc_type = sqlite3.OperationalError
        exc_value = sqlite3.OperationalError("database is locked")
        # Scenario: Low memory + DB error
        diagnosis = {"low_memory": True, "available_mem_mb": 10}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        # OOM should be prioritized or at least highly probable (85 score in code)
        oom_cause = next((c for c in causes if "OOM" in c["description"]), None)
        self.assertIsNotNone(oom_cause)
        self.assertEqual(oom_cause["score"], 85)

    def test_heuristic_analysis_memoryerror(self):
        causes = self.recovery._analyze_cause(
            MemoryError,
            MemoryError("unable to allocate array"),
            {"low_memory": False, "available_mem_mb": 1024},
        )
        oom_cause = next((c for c in causes if "OOM" in c["description"]), None)
        self.assertIsNotNone(oom_cause)
        self.assertEqual(oom_cause["score"], 95)

    def test_heuristic_analysis_rns_missing(self):
        """Verify high confidence for missing RNS config."""
        exc_type = RuntimeError
        exc_value = RuntimeError("Reticulum could not start")
        diagnosis = {"config_missing": True}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertEqual(causes[0]["description"], "Missing Reticulum Configuration")
        self.assertEqual(causes[0]["score"], 99)

    def test_heuristic_analysis_permission_denied_priority(self):
        exc_type = PermissionError
        exc_value = PermissionError(13, "Permission denied", "/config/.meshchat")
        diagnosis = {"config_missing": True, "permission_denied": True}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertEqual(causes[0]["description"], "Filesystem Permission Denied")
        self.assertEqual(causes[0]["score"], 99)

    def test_run_diagnosis_permission_crash_context(self):
        output = io.StringIO()
        exc = PermissionError(13, "Permission denied", "/data/meshchat")
        self.recovery.run_diagnosis(file=output, crash_exception=exc)
        report = output.getvalue()
        self.assertIn("Filesystem permission failure", report)
        self.assertIn("/data/meshchat", report)

    def test_entropy_calculation_levels(self):
        """Test how entropy reflects system disorder."""
        # Baseline stable state
        stable_diag = {"low_memory": False, "config_missing": False}
        stable_entropy, _ = self.recovery._calculate_system_entropy(stable_diag)

        # Unstable state (one critical issue)
        unstable_diag = {"low_memory": True, "config_missing": False}
        unstable_entropy, _ = self.recovery._calculate_system_entropy(unstable_diag)

        # Very unstable state (multiple critical issues)
        very_unstable_diag = {"low_memory": True, "config_missing": True}
        very_unstable_entropy, _ = self.recovery._calculate_system_entropy(
            very_unstable_diag,
        )

        # Entropy should increase with more issues
        self.assertGreater(unstable_entropy, stable_entropy)
        self.assertGreater(very_unstable_entropy, unstable_entropy)

        # Max entropy for 2 binary states is at p=0.5, but here we sum
        # p_unstable = 0.1 + 0.4 + 0.4 = 0.9.
        # p=0.9 has lower entropy than p=0.5, but higher than p=0.1.
        # p_stable=0.9 (stable) vs p_stable=0.5 (medium) vs p_stable=0.1 (unstable)
        # H(0.1) = 0.469, H(0.5) = 1.0, H(0.9) = 0.469
        # The current implementation:
        # stable: p_unstable=0.1 -> H=0.469
        # unstable: p_unstable=0.5 -> H=1.0
        # very unstable: p_unstable=0.9 -> H=0.469 (wait, mathematically yes, but logically?)
        # Actually for a "disorder" metric, we might want it to peak when things are most uncertain.
        # But in our context, we are showing entropy of the "State Predictability".

    def test_heuristic_analysis_lxmf_storage(self):
        """Test LXMF storage failure detection."""
        exc_type = RuntimeError
        exc_value = RuntimeError("LXMF could not open storage directory")
        diagnosis = {}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertEqual(causes[0]["description"], "LXMF Router Storage Failure")
        self.assertEqual(causes[0]["score"], 90)

    def test_heuristic_analysis_rns_identity(self):
        """Test Reticulum identity failure detection."""
        exc_type = Exception
        exc_value = Exception("Reticulum Identity load failed: corrupt private key")
        diagnosis = {}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertEqual(causes[0]["description"], "Reticulum Identity Load Failure")
        self.assertEqual(causes[0]["score"], 95)

    def test_heuristic_analysis_interface_offline(self):
        """Test interface offline detection."""
        exc_type = RuntimeError
        exc_value = RuntimeError("Reticulum startup failed")
        diagnosis = {"active_interfaces": 0}

        # We need to trigger the rns_in_msg symptom as well
        exc_value = RuntimeError("Reticulum failed, no path available")
        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)

        offline_cause = next(
            (c for c in causes if "Interface" in c["description"]),
            None,
        )
        self.assertIsNotNone(offline_cause)
        self.assertEqual(offline_cause["score"], 85)

    def test_advanced_math_output(self):
        # We don't want to actually sys.exit(1) in tests, so we mock it
        original_exit = sys.exit
        sys.exit = MagicMock()

        output = io.StringIO()
        # Redirect stderr to our buffer
        original_stderr = sys.stderr
        sys.stderr = output

        try:
            try:
                raise RuntimeError("no current event loop")
            except RuntimeError:
                self.recovery.handle_exception(*sys.exc_info())
        finally:
            sys.stderr = original_stderr
            sys.exit = original_exit

        report = output.getvalue()
        self.assertIn("[System Entropy:", report)
        self.assertIn("[KL-Divergence:", report)

    def test_heuristic_analysis_unsupported_python(self):
        """Test detection of unsupported Python versions."""
        # We need to simulate the sys.version_info check
        with patch("sys.version_info") as mock_version:
            mock_version.major = 3
            mock_version.minor = 9

            exc_type = AttributeError
            exc_value = AttributeError("'NoneType' object has no attribute 'x'")
            diagnosis = {}

            causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
            self.assertEqual(causes[0]["description"], "Unsupported Python Environment")
            self.assertEqual(causes[0]["score"], 99)
            self.assertIn(
                "missing standard library features",
                causes[0]["reasoning"].lower(),
            )

    def test_heuristic_analysis_legacy_kernel(self):
        """Test detection of legacy system/kernel limitations."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.release", return_value="3.10.0-1160.el7.x86_64"),
        ):
            exc_type = RuntimeError
            exc_value = RuntimeError("kernel feature not available")
            diagnosis = {}

            causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
            legacy_cause = next(
                (c for c in causes if "Legacy System" in c["description"]),
                None,
            )
            self.assertIsNotNone(legacy_cause)
            self.assertGreaterEqual(legacy_cause["score"], 80)
            self.assertIn("Kernel detected: 3.10", legacy_cause["reasoning"])

    # ==================================================================
    # install() / disable()
    # ==================================================================

    def test_install_sets_excepthook(self):
        """install() should set sys.excepthook to handle_exception."""
        original = sys.excepthook
        original_unraisable = sys.unraisablehook
        try:
            self.recovery.install()
            self.assertEqual(sys.excepthook, self.recovery.handle_exception)
        finally:
            sys.excepthook = original
            sys.unraisablehook = original_unraisable
            self.recovery._prev_sys_hook = None
            self.recovery._prev_unraisable_hook = None

    def test_disable_prevents_install(self):
        """After disable(), install() should not set the hook."""
        original = sys.excepthook
        try:
            self.recovery.disable()
            self.recovery.install()
            self.assertNotEqual(sys.excepthook, self.recovery.handle_exception)
        finally:
            sys.excepthook = original

    # ==================================================================
    # _calculate_system_entropy edge cases
    # ==================================================================

    def test_entropy_empty_diagnosis(self):
        """Empty diagnosis should return baseline entropy (all ideal)."""
        entropy, divergence = self.recovery._calculate_system_entropy({})
        self.assertGreater(entropy, 0)
        self.assertAlmostEqual(divergence, 0.0, places=5)

    def test_entropy_all_critical(self):
        """All dimensions critical should maximize entropy and divergence."""
        diag = {
            "low_memory": True,
            "config_missing": True,
            "db_type": "memory",
        }
        entropy, divergence = self.recovery._calculate_system_entropy(diag)
        base_entropy, base_div = self.recovery._calculate_system_entropy({})
        self.assertGreater(entropy, base_entropy)
        self.assertGreater(divergence, base_div)

    def test_entropy_invalid_mem_value(self):
        """Non-numeric available_mem_mb should not crash."""
        diag = {"available_mem_mb": "not_a_number", "low_memory": True}
        entropy, divergence = self.recovery._calculate_system_entropy(diag)
        self.assertIsInstance(entropy, float)
        self.assertIsInstance(divergence, float)

    def test_entropy_none_mem_value(self):
        """None available_mem_mb should not crash."""
        diag = {"available_mem_mb": None}
        entropy, _divergence = self.recovery._calculate_system_entropy(diag)
        self.assertIsInstance(entropy, float)

    def test_divergence_nonnegative(self):
        """KL divergence must always be non-negative."""
        test_cases = [
            {},
            {"low_memory": True},
            {"config_missing": True},
            {"db_type": "memory"},
            {"low_memory": True, "config_missing": True, "db_type": "memory"},
        ]
        for diag in test_cases:
            _, div = self.recovery._calculate_system_entropy(diag)
            self.assertGreaterEqual(div, 0.0, f"Negative divergence for {diag}")

    # ==================================================================
    # legacy_kernel regex safety
    # ==================================================================

    def test_legacy_kernel_non_linux(self):
        """Non-Linux platforms should not crash on legacy_kernel check."""
        with (
            patch("platform.system", return_value="Windows"),
            patch("platform.release", return_value="10"),
        ):
            exc_type = RuntimeError
            exc_value = RuntimeError("test")
            causes = self.recovery._analyze_cause(exc_type, exc_value, {})
            self.assertIsInstance(causes, list)

    def test_legacy_kernel_unusual_release(self):
        """Unusual release strings should not crash."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.release", return_value="unknown"),
        ):
            exc_type = RuntimeError
            exc_value = RuntimeError("test")
            causes = self.recovery._analyze_cause(exc_type, exc_value, {})
            self.assertIsInstance(causes, list)

    def test_legacy_kernel_empty_release(self):
        """Empty release string should not crash."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.release", return_value=""),
        ):
            exc_type = RuntimeError
            exc_value = RuntimeError("test")
            causes = self.recovery._analyze_cause(exc_type, exc_value, {})
            self.assertIsInstance(causes, list)

    # ==================================================================
    # run_reticulum_diagnosis isolation
    # ==================================================================

    def test_reticulum_diagnosis_invalid_config_content(self):
        """Invalid config file content should be flagged."""
        rns_dir = os.path.join(self.test_dir, "rns_invalid")
        os.makedirs(rns_dir)
        with open(os.path.join(rns_dir, "config"), "w") as f:
            f.write("this is not a valid reticulum config")

        self.recovery.update_paths(reticulum_config_dir=rns_dir)
        output = io.StringIO()
        results = self.recovery.run_reticulum_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("[ERROR]", report)
        self.assertTrue(results.get("config_invalid", False))

    def test_reticulum_diagnosis_empty_logfile(self):
        """Empty log file should be handled gracefully."""
        rns_dir = os.path.join(self.test_dir, "rns_empty_log")
        os.makedirs(rns_dir)
        with open(os.path.join(rns_dir, "config"), "w") as f:
            f.write("[reticulum]\n")
        with open(os.path.join(rns_dir, "logfile"), "w") as f:
            pass

        self.recovery.update_paths(reticulum_config_dir=rns_dir)
        output = io.StringIO()
        self.recovery.run_reticulum_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("Log file is empty", report)

    # ==================================================================
    # Diagnosis edge cases
    # ==================================================================

    def test_diagnosis_empty_db_file(self):
        """0-byte database file should trigger a warning."""
        open(self.db_path, "w").close()

        output = io.StringIO()
        self.recovery.run_diagnosis(file=output)
        report = output.getvalue()
        self.assertIn("empty (0 bytes)", report)

    def test_update_paths(self):
        """update_paths should correctly update internal state."""
        new_storage = os.path.join(self.test_dir, "new_storage")
        self.recovery.update_paths(storage_dir=new_storage)
        self.assertEqual(self.recovery.storage_dir, new_storage)

    def test_keyboard_interrupt_passthrough(self):
        """KeyboardInterrupt should be passed to the default hook."""
        called = {}

        def mock_hook(exc_type, exc_value, exc_tb):
            called["invoked"] = True

        original = sys.__excepthook__
        sys.__excepthook__ = mock_hook
        try:
            self.recovery.handle_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
            self.assertTrue(called.get("invoked", False))
        finally:
            sys.__excepthook__ = original

    # ==================================================================
    # Hook lifecycle and report content regressions
    # ==================================================================

    def test_disable_restores_sys_excepthook(self):
        """disable() must undo install() for sys.excepthook, not only threads."""
        original = sys.excepthook
        original_threading = threading.excepthook
        original_unraisable = sys.unraisablehook
        try:
            self.recovery.install()
            self.assertEqual(sys.excepthook, self.recovery.handle_exception)
            self.recovery.disable()
            self.assertIs(sys.excepthook, original)
            self.assertIs(sys.unraisablehook, original_unraisable)
        finally:
            sys.excepthook = original
            threading.excepthook = original_threading
            sys.unraisablehook = original_unraisable

    def test_handle_exception_skipped_when_disabled(self):
        """A disabled recovery must not emit reports."""
        self.recovery.enabled = False
        output = io.StringIO()
        original_stderr = sys.stderr
        original_exit = sys.exit
        sys.stderr = output
        sys.exit = lambda x: None
        try:
            self.recovery.handle_exception(ValueError, ValueError("x"), None)
        finally:
            sys.stderr = original_stderr
            sys.exit = original_exit
        self.assertNotIn("APPLICATION CRASH DETECTED", output.getvalue())

    def test_analyze_cause_never_empty(self):
        """An unrecognized error must still list at least one candidate."""
        causes = self.recovery._analyze_cause(
            ValueError,
            ValueError("totally unrecognized frobnicate failure"),
            {},
        )
        self.assertTrue(len(causes) > 0)

    def test_cross_loop_bound_message_maps_to_cross_loop_cause(self):
        """'bound to a different event loop' is a cross-loop binding error."""
        exc_value = RuntimeError(
            "<asyncio.locks.Lock object [unlocked, waiters:1]> "
            "is bound to a different event loop",
        )
        causes = self.recovery._analyze_cause(RuntimeError, exc_value, {})
        self.assertTrue(len(causes) > 0)
        top = causes[0]["description"]
        self.assertIn("Cross-Loop", top)
        self.assertNotIn("Initialization", top)

    def test_persist_crash_stores_symptoms(self):
        """Matched symptoms must reach crash_history, not an empty dict."""
        inserted = []

        class CrashHistory:
            def insert_crash(self, **kwargs):
                inserted.append(kwargs)

            def cleanup_old(self, max_entries=200):
                pass

        db = MagicMock()
        db.crash_history = CrashHistory()
        db.config.get.return_value = None
        self.recovery.set_database(db)

        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            try:
                raise ValueError("no running event loop in asyncio")
            except ValueError:
                self.recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original_stderr

        self.assertEqual(len(inserted), 1)
        symptoms = inserted[0]["symptoms"]
        self.assertIsInstance(symptoms, dict)
        self.assertTrue(symptoms.get("async_in_msg"))

    # ==================================================================
    # Signatures, suppression, normalization, report files
    # ==================================================================

    def test_crash_signature_stable_for_same_site(self):
        """Same raising frame must yield the same signature."""

        def boom():
            raise RuntimeError("same crash")

        signatures = []
        for _ in range(2):
            try:
                boom()
            except RuntimeError:
                signatures.append(
                    self.recovery._crash_signature(*sys.exc_info()),
                )
        self.assertEqual(signatures[0], signatures[1])
        self.assertEqual(len(signatures[0]), 16)

    def test_repeat_signature_suppressed_but_persisted(self):
        """A second same-signature crash prints one line, not a report."""
        inserted = []

        class CrashHistory:
            def insert_crash(self, **kwargs):
                inserted.append(kwargs)

            def cleanup_old(self, max_entries=200):
                pass

            def get_recent_crashes(self, limit=200):
                return []

        db = MagicMock()
        db.crash_history = CrashHistory()
        db.config.get.return_value = None
        self.recovery.set_database(db)

        def boom():
            raise ValueError("repeat crash")

        original_stderr = sys.stderr
        first = io.StringIO()
        second = io.StringIO()
        try:
            sys.stderr = first
            try:
                boom()
            except ValueError:
                self.recovery.handle_exception(*sys.exc_info(), exit_process=False)
            sys.stderr = second
            try:
                boom()
            except ValueError:
                self.recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original_stderr

        self.assertIn("APPLICATION CRASH DETECTED", first.getvalue())
        self.assertIn("suppressed", second.getvalue())
        self.assertNotIn("APPLICATION CRASH DETECTED", second.getvalue())
        self.assertEqual(len(inserted), 2)
        self.assertEqual(
            inserted[0]["symptoms"].get("_signature"),
            inserted[1]["symptoms"].get("_signature"),
        )

    def test_report_written_to_crash_reports_dir(self):
        """Full report must land in storage_dir/crash_reports/."""
        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            try:
                raise RuntimeError("filed report crash")
            except RuntimeError:
                self.recovery.handle_exception(*sys.exc_info(), exit_process=False)
        finally:
            sys.stderr = original_stderr

        report_dir = os.path.join(self.storage_dir, "crash_reports")
        files = os.listdir(report_dir)
        self.assertEqual(len(files), 1)
        with open(os.path.join(report_dir, files[0])) as f:
            content = f.read()
        self.assertIn("APPLICATION CRASH DETECTED", content)
        self.assertIn("Crash Signature:", content)

    def test_probabilities_normalized_and_sorted(self):
        """Shares are bounded by 100 and sorted by raw score."""
        causes = self.recovery._analyze_cause(
            MemoryError,
            MemoryError("cannot allocate"),
            {"low_memory": True},
        )
        total = sum(c["probability"] for c in causes)
        self.assertLessEqual(total, 100)
        scores = [c["score"] for c in causes]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertIn("OOM", causes[0]["description"])
        # A dominant single cause still presents as dominant, not ~100%.
        self.assertLess(causes[0]["probability"], 100)
        self.assertGreater(
            causes[0]["probability"],
            causes[1]["probability"] if len(causes) > 1 else 0,
        )

    def test_traceback_frames_boost_matching_subsystem(self):
        """A crash whose frames live in database/ should lift DB causes."""
        src = "def f():\n    raise ValueError('generic failure')\nf()\n"
        code = compile(
            src,
            "/pkg/meshchatx/src/backend/database/messages.py",
            "exec",
        )
        causes = []
        try:
            exec(code, {})
        except ValueError as exc:
            causes = self.recovery._analyze_cause(
                ValueError,
                exc,
                {},
                exc_traceback=exc.__traceback__,
            )
        db_causes = [c for c in causes if "Database" in c["description"]]
        self.assertTrue(db_causes)
        self.assertGreaterEqual(db_causes[0]["score"], 50)

    def test_asyncio_handler_routes_real_exceptions(self):
        """Loop handler reports real exceptions and defers noise."""
        loop = MagicMock()
        output = io.StringIO()
        original_stderr = sys.stderr
        sys.stderr = output
        try:
            try:
                raise ValueError("task blew up")
            except ValueError as exc:
                self.recovery.handle_asyncio_exception(
                    loop,
                    {"exception": exc},
                )
        finally:
            sys.stderr = original_stderr
        self.assertIn("APPLICATION CRASH DETECTED", output.getvalue())

        loop.default_exception_handler.reset_mock()
        self.recovery.handle_asyncio_exception(
            loop,
            {"message": "Task was destroyed but it is pending"},
        )
        loop.default_exception_handler.assert_called_once()

    def test_unraisable_hook_routes_through_handler(self):
        """sys.unraisablehook entries reach the diagnosis path."""
        import types

        output = io.StringIO()
        original_stderr = sys.stderr
        sys.stderr = output
        try:
            try:
                raise ValueError("gc side failure")
            except ValueError:
                exc_type, exc_value, exc_tb = sys.exc_info()
            args = types.SimpleNamespace(
                exc_type=exc_type,
                exc_value=exc_value,
                exc_traceback=exc_tb,
                err_msg=None,
                object=None,
            )
            self.recovery._handle_unraisable(args)
        finally:
            sys.stderr = original_stderr
        self.assertIn("APPLICATION CRASH DETECTED", output.getvalue())

    def test_learned_weights_clamped_and_confident_only(self):
        """Self-labeled priors must be bounded and confidence-gated."""
        captured = {}

        class Config:
            def get(self, key):
                return None

            def set(self, key, value):
                captured[key] = value

        class CrashHistory:
            def get_cause_frequencies(self, limit=50, min_probability=None):
                assert min_probability == 60
                return [
                    {
                        "diagnosed_cause": "SQLite Database Corruption",
                        "count": 40,
                    },
                ]

        db = MagicMock()
        db.crash_history = CrashHistory()
        db.config = Config()
        self.recovery.set_database(db)

        self.recovery._update_learned_weights()

        weights = json.loads(captured["diagnostic_weights"])
        # 40/42 confident hits would be ~0.95 unbounded; the guardrail caps
        # learned drift at 4x the default prior (0.05 -> 0.20) and floors a
        # cause with no hits at 0.25x its default (0.10 -> 0.025).
        self.assertEqual(weights["DB_CORRUPTION"], 0.2)
        self.assertEqual(weights["ASYNC_RACE"], 0.025)


if __name__ == "__main__":
    unittest.main()
