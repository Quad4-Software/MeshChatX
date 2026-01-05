import logging
import time

import pytest

from meshchatx.src.backend.database import Database
from meshchatx.src.backend.persistent_log_handler import PersistentLogHandler


@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test_logs.db"
    database = Database(str(db_file))
    database.initialize()
    return database


@pytest.fixture
def handler(db):
    handler = PersistentLogHandler(database=db, flush_interval=0.1)
    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return handler, logger


def test_log_insertion(handler, db):
    persistent_handler, logger = handler
    logger.info("Test message")

    # Wait for flush
    time.sleep(0.2)
    logger.info("Trigger flush")  # emit triggers flush if interval passed

    logs = persistent_handler.get_logs(limit=10)
    assert len(logs) >= 2
    # Logs are descending by timestamp, so newer is first
    messages = [log["message"] for log in logs]
    assert "Test message" in messages
    assert "Trigger flush" in messages


def test_search_and_filter(handler, db):
    persistent_handler, logger = handler
    logger.info("Hello world")
    logger.error("Something went wrong")

    time.sleep(0.2)
    logger.debug("Force flush")

    # Search
    results = persistent_handler.get_logs(search="world")
    assert len(results) == 1
    assert "Hello world" in results[0]["message"]

    # Filter by level
    results = persistent_handler.get_logs(level="ERROR")
    assert len(results) == 1
    assert "Something went wrong" in results[0]["message"]


def test_anomaly_flooding(handler, db):
    persistent_handler, logger = handler
    persistent_handler.flooding_threshold = 5

    for i in range(10):
        logger.warning(f"Message {i}")

    # Wait for flush
    logger.debug("Force flush")

    logs = persistent_handler.get_logs(limit=20)
    anomalies = [log for log in logs if log["is_anomaly"]]
    assert len(anomalies) > 0
    assert any(log["anomaly_type"] == "flooding" for log in anomalies)


def test_anomaly_repeat(handler, db):
    persistent_handler, logger = handler
    persistent_handler.repeat_threshold = 3

    for _ in range(5):
        logger.warning("Same message")

    # Wait for flush
    logger.debug("Force flush")

    logs = persistent_handler.get_logs(limit=20)
    anomalies = [log for log in logs if log["is_anomaly"]]
    assert len(anomalies) > 0
    assert any(log["anomaly_type"] == "repeat" for log in anomalies)


def test_log_cleanup(handler, db):
    persistent_handler, logger = handler

    # Insert many logs
    for i in range(100):
        logger.info(f"Log {i}")

    time.sleep(0.2)
    logger.debug("Trigger cleanup")

    # Force cleanup with small limit
    db.debug_logs.cleanup_old_logs(max_logs=10)

    count = db.debug_logs.get_total_count()
    assert count <= 11  # 10 + the trigger log
