# SPDX-License-Identifier: 0BSD

import json
import os
import shutil
import tempfile
import time
import unittest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.recovery.crash_recovery import _DEFAULT_PRIORS, CrashRecovery


class TestCrashHistoryDAO(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_crash.db")
        self.db = Database(self.db_path)
        self.db.initialize()

    def tearDown(self):
        self.db.close_all()
        shutil.rmtree(self.test_dir)

    def test_insert_and_retrieve(self):
        self.db.crash_history.insert_crash(
            timestamp=time.time(),
            error_type="ValueError",
            error_message="test error",
            diagnosed_cause="DB_CORRUPTION",
            symptoms={"sqlite_in_msg": True},
            probability=85,
            entropy=1.234,
            divergence=0.567,
        )
        rows = self.db.crash_history.get_recent_crashes(limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_type"], "ValueError")
        self.assertEqual(rows[0]["diagnosed_cause"], "DB_CORRUPTION")
        self.assertEqual(rows[0]["probability"], 85)

    def test_get_cause_frequencies(self):
        now = time.time()
        for i in range(5):
            self.db.crash_history.insert_crash(
                timestamp=now + i,
                error_type="E",
                error_message="m",
                diagnosed_cause="DB_CORRUPTION",
                symptoms={},
                probability=50,
                entropy=0.0,
                divergence=0.0,
            )
        for i in range(3):
            self.db.crash_history.insert_crash(
                timestamp=now + 10 + i,
                error_type="E",
                error_message="m",
                diagnosed_cause="OOM",
                symptoms={},
                probability=30,
                entropy=0.0,
                divergence=0.0,
            )
        freqs = self.db.crash_history.get_cause_frequencies(limit=50)
        freq_map = {r["diagnosed_cause"]: r["count"] for r in freqs}
        self.assertEqual(freq_map["DB_CORRUPTION"], 5)
        self.assertEqual(freq_map["OOM"], 3)

    def test_cleanup_old(self):
        now = time.time()
        for i in range(20):
            self.db.crash_history.insert_crash(
                timestamp=now + i,
                error_type="E",
                error_message="m",
                diagnosed_cause="X",
                symptoms={},
                probability=0,
                entropy=0.0,
                divergence=0.0,
            )
        self.db.crash_history.cleanup_old(max_entries=5)
        rows = self.db.crash_history.get_recent_crashes(limit=100)
        self.assertEqual(len(rows), 5)

    def test_insert_long_error_message_truncated(self):
        long_msg = "x" * 1000
        self.db.crash_history.insert_crash(
            timestamp=time.time(),
            error_type="E",
            error_message=long_msg,
            diagnosed_cause="X",
            symptoms={},
            probability=0,
            entropy=0.0,
            divergence=0.0,
        )
        rows = self.db.crash_history.get_recent_crashes()
        self.assertLessEqual(len(rows[0]["error_message"]), 500)

    def test_symptoms_stored_as_json(self):
        syms = {"sqlite_in_msg": True, "low_mem": False}
        self.db.crash_history.insert_crash(
            timestamp=time.time(),
            error_type="E",
            error_message="m",
            diagnosed_cause="X",
            symptoms=syms,
            probability=0,
            entropy=0.0,
            divergence=0.0,
        )
        rows = self.db.crash_history.get_recent_crashes()
        loaded = json.loads(rows[0]["symptoms"])
        self.assertEqual(loaded, syms)


class TestBayesianWeightLearning(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_bayes.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.recovery = CrashRecovery(
            storage_dir=self.test_dir,
            database_path=self.db_path,
            database=self.db,
        )

    def tearDown(self):
        self.db.close_all()
        shutil.rmtree(self.test_dir)

    def test_get_prior_defaults(self):
        for key, default_val in _DEFAULT_PRIORS.items():
            self.assertEqual(self.recovery._get_prior(key), default_val)

    def test_get_prior_learned(self):
        self.recovery._learned_priors = {"DB_CORRUPTION": 0.42}
        self.assertEqual(self.recovery._get_prior("DB_CORRUPTION"), 0.42)
        self.assertEqual(self.recovery._get_prior("OOM"), _DEFAULT_PRIORS["OOM"])

    def test_update_learned_weights_no_data(self):
        self.recovery._update_learned_weights()
        self.assertIsNone(self.recovery._learned_priors)

    def test_update_learned_weights_with_history(self):
        now = time.time()
        desc = CrashRecovery._cause_key_to_description("DB_CORRUPTION")
        for i in range(10):
            self.db.crash_history.insert_crash(
                timestamp=now + i,
                error_type="E",
                error_message="m",
                diagnosed_cause=desc,
                symptoms={},
                probability=50,
                entropy=0.0,
                divergence=0.0,
            )
        self.recovery._update_learned_weights()
        self.assertIsNotNone(self.recovery._learned_priors)
        self.assertGreater(self.recovery._learned_priors["DB_CORRUPTION"], 0.01)
        self.assertLessEqual(self.recovery._learned_priors["DB_CORRUPTION"], 0.99)

    def test_weights_clamped(self):
        now = time.time()
        desc = CrashRecovery._cause_key_to_description("DB_CORRUPTION")
        for i in range(50):
            self.db.crash_history.insert_crash(
                timestamp=now + i,
                error_type="E",
                error_message="m",
                diagnosed_cause=desc,
                symptoms={},
                probability=99,
                entropy=0.0,
                divergence=0.0,
            )
        self.recovery._update_learned_weights()
        for v in self.recovery._learned_priors.values():
            self.assertGreaterEqual(v, 0.01)
            self.assertLessEqual(v, 0.99)

    def test_load_learned_priors_from_config(self):
        weights = {"DB_CORRUPTION": 0.55, "OOM": 0.12}
        self.db.config.set("diagnostic_weights", json.dumps(weights))
        self.recovery._load_learned_priors()
        self.assertEqual(self.recovery._learned_priors, weights)

    def test_load_learned_priors_no_config(self):
        self.recovery._load_learned_priors()
        self.assertIsNone(self.recovery._learned_priors)

    def test_set_database_loads_priors(self):
        weights = {"DB_CORRUPTION": 0.33}
        self.db.config.set("diagnostic_weights", json.dumps(weights))
        new_recovery = CrashRecovery()
        new_recovery.set_database(self.db)
        self.assertEqual(new_recovery._learned_priors, weights)

    def test_persist_crash(self):
        causes = [
            {"description": "Test Cause", "probability": 75},
        ]
        self.recovery._persist_crash("TypeError", "test msg", causes, {}, 1.5, 0.3)
        rows = self.db.crash_history.get_recent_crashes()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["diagnosed_cause"], "Test Cause")
        self.assertEqual(rows[0]["probability"], 75)

    def test_persist_crash_no_db(self):
        recovery_no_db = CrashRecovery()
        recovery_no_db._persist_crash("E", "m", [], {}, 0.0, 0.0)

    def test_cause_key_to_description_mapping(self):
        for key in _DEFAULT_PRIORS:
            desc = CrashRecovery._cause_key_to_description(key)
            self.assertNotEqual(desc, key)
            self.assertIsInstance(desc, str)

    def test_cause_key_to_description_unknown(self):
        self.assertEqual(
            CrashRecovery._cause_key_to_description("UNKNOWN_KEY"),
            "UNKNOWN_KEY",
        )

    def test_update_weights_needs_min_3_crashes(self):
        now = time.time()
        desc = CrashRecovery._cause_key_to_description("DB_CORRUPTION")
        for i in range(2):
            self.db.crash_history.insert_crash(
                timestamp=now + i,
                error_type="E",
                error_message="m",
                diagnosed_cause=desc,
                symptoms={},
                probability=50,
                entropy=0.0,
                divergence=0.0,
            )
        self.recovery._update_learned_weights()
        self.assertIsNone(self.recovery._learned_priors)


if __name__ == "__main__":
    unittest.main()
