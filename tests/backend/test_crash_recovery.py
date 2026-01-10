import io
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

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
        self.assertIn("Recovery Suggestions:", report)


if __name__ == "__main__":
    unittest.main()
