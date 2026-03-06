import io
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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
        """Verify that low memory increases OOM probability even with other errors."""
        exc_type = sqlite3.OperationalError
        exc_value = sqlite3.OperationalError("database is locked")
        # Scenario: Low memory + DB error
        diagnosis = {"low_memory": True, "available_mem_mb": 10}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        # OOM should be prioritized or at least highly probable (85% in code)
        oom_cause = next((c for c in causes if "OOM" in c["description"]), None)
        self.assertIsNotNone(oom_cause)
        self.assertEqual(oom_cause["probability"], 85)

    def test_heuristic_analysis_rns_missing(self):
        """Verify high confidence for missing RNS config."""
        exc_type = RuntimeError
        exc_value = RuntimeError("Reticulum could not start")
        diagnosis = {"config_missing": True}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertEqual(causes[0]["description"], "Missing Reticulum Configuration")
        self.assertEqual(causes[0]["probability"], 99)

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
        self.assertEqual(causes[0]["probability"], 90)

    def test_heuristic_analysis_rns_identity(self):
        """Test Reticulum identity failure detection."""
        exc_type = Exception
        exc_value = Exception("Reticulum Identity load failed: corrupt private key")
        diagnosis = {}

        causes = self.recovery._analyze_cause(exc_type, exc_value, diagnosis)
        self.assertEqual(causes[0]["description"], "Reticulum Identity Load Failure")
        self.assertEqual(causes[0]["probability"], 95)

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
        self.assertEqual(offline_cause["probability"], 85)

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
            self.assertEqual(causes[0]["probability"], 99)
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
            self.assertGreaterEqual(legacy_cause["probability"], 80)
            self.assertIn("Kernel detected: 3.10", legacy_cause["reasoning"])

    # ==================================================================
    # install() / disable()
    # ==================================================================

    def test_install_sets_excepthook(self):
        """install() should set sys.excepthook to handle_exception."""
        original = sys.excepthook
        try:
            self.recovery.install()
            self.assertEqual(sys.excepthook, self.recovery.handle_exception)
        finally:
            sys.excepthook = original

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
        entropy, divergence = self.recovery._calculate_system_entropy(diag)
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
        open(self.db_path, "w").close()  # noqa: SIM115

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


if __name__ == "__main__":
    unittest.main()
