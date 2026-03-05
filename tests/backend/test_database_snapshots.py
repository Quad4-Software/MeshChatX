import json
import os
import shutil
import tempfile

import pytest

from meshchatx.src.backend.database import Database


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


def test_database_snapshot_creation(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()

    # Add some data
    db.execute_sql(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        ("test_key", "test_value"),
    )

    # Create snapshot
    snapshot_name = "test_snapshot"
    db.create_snapshot(temp_dir, snapshot_name)

    snapshot_path = os.path.join(temp_dir, "snapshots", f"{snapshot_name}.zip")
    assert os.path.exists(snapshot_path)

    # List snapshots
    snapshots = db.list_snapshots(temp_dir)
    assert len(snapshots) == 1
    assert snapshots[0]["name"] == snapshot_name


def test_database_snapshot_restoration(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()

    # Add some data
    db.execute_sql("INSERT INTO config (key, value) VALUES (?, ?)", ("v1", "original"))

    # Create snapshot
    db.create_snapshot(temp_dir, "snap1")
    snapshot_path = os.path.join(temp_dir, "snapshots", "snap1.zip")

    # Modify data
    db.execute_sql("UPDATE config SET value = ? WHERE key = ?", ("modified", "v1"))
    row = db.provider.fetchone("SELECT value FROM config WHERE key = ?", ("v1",))
    assert row["value"] == "modified"

    # Restore snapshot
    db.restore_database(snapshot_path)

    # Verify data is back to original
    row = db.provider.fetchone("SELECT value FROM config WHERE key = ?", ("v1",))
    assert row is not None
    assert row["value"] == "original"


def test_database_auto_backup_logic(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()

    # Should create a timestamped backup
    result = db.backup_database(temp_dir)
    assert "database-backups" in result["path"]
    assert os.path.exists(result["path"])

    backup_dir = os.path.join(temp_dir, "database-backups")
    zips = [f for f in os.listdir(backup_dir) if f.endswith(".zip")]
    assert len(zips) == 1


def test_backup_baseline_created_on_first_backup(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    db.backup_database(temp_dir)
    baseline_path = os.path.join(temp_dir, "database-backups", "backup-baseline.json")
    assert os.path.exists(baseline_path)
    with open(baseline_path) as f:
        data = json.load(f)
    assert "message_count" in data
    assert "total_bytes" in data
    assert "timestamp" in data


def test_backup_suspicious_when_messages_gone_skips_cleanup_and_baseline(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    db.messages.upsert_lxmf_message(
        {
            "hash": "h1",
            "source_hash": "s",
            "destination_hash": "d",
            "peer_hash": "p",
            "state": "delivered",
            "progress": 1.0,
            "is_incoming": 1,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": "{}",
            "timestamp": 0,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
        }
    )
    result1 = db.backup_database(temp_dir, max_count=3)
    assert result1.get("suspicious") is not True
    backup_dir = os.path.join(temp_dir, "database-backups")
    zip_count_after_first = sum(1 for f in os.listdir(backup_dir) if f.endswith(".zip"))
    assert zip_count_after_first == 1
    with open(os.path.join(backup_dir, "backup-baseline.json")) as f:
        baseline_after_first = json.load(f)
    assert baseline_after_first["message_count"] == 1

    db.messages.delete_all_lxmf_messages()
    assert db.messages.count_lxmf_messages() == 0
    result2 = db.backup_database(temp_dir, max_count=3)
    assert result2.get("suspicious") is True
    assert "baseline" in result2
    assert result2["baseline"]["message_count"] == 1
    assert result2["current_stats"]["message_count"] == 0
    zip_count_after_suspicious = sum(
        1 for f in os.listdir(backup_dir) if f.endswith(".zip")
    )
    assert zip_count_after_suspicious == 2
    assert any("SUSPICIOUS" in f for f in os.listdir(backup_dir) if f.endswith(".zip"))
    with open(os.path.join(backup_dir, "backup-baseline.json")) as f:
        baseline_after_suspicious = json.load(f)
    assert baseline_after_suspicious["message_count"] == 1


def test_backup_suspicious_when_size_collapsed_skips_cleanup(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    for i in range(200):
        db.messages.upsert_lxmf_message(
            {
                "hash": f"h{i}",
                "source_hash": "s",
                "destination_hash": "d",
                "peer_hash": "p",
                "state": "delivered",
                "progress": 1.0,
                "is_incoming": 1,
                "method": "direct",
                "delivery_attempts": 0,
                "next_delivery_attempt_at": None,
                "title": "t",
                "content": "x" * 500,
                "fields": "{}",
                "timestamp": float(i),
                "rssi": None,
                "snr": None,
                "quality": None,
                "is_spam": 0,
                "reply_to_hash": None,
            }
        )
    db.backup_database(temp_dir, max_count=3)
    baseline_path = os.path.join(temp_dir, "database-backups", "backup-baseline.json")
    with open(baseline_path) as f:
        baseline = json.load(f)
    assert baseline["total_bytes"] > 100_000
    db.messages.delete_all_lxmf_messages()
    db.execute_sql("VACUUM")
    result = db.backup_database(temp_dir, max_count=3)
    assert result.get("suspicious") is True
    backup_dir = os.path.join(temp_dir, "database-backups")
    zips = [f for f in os.listdir(backup_dir) if f.endswith(".zip")]
    assert len(zips) >= 2


def test_backup_normal_rotation_and_baseline_update(temp_dir):
    import time

    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    db.backup_database(temp_dir, max_count=2)
    time.sleep(1.1)
    db.backup_database(temp_dir, max_count=2)
    time.sleep(1.1)
    db.backup_database(temp_dir, max_count=2)
    backup_dir = os.path.join(temp_dir, "database-backups")
    zips = sorted([f for f in os.listdir(backup_dir) if f.endswith(".zip")])
    assert len(zips) == 2
    assert os.path.exists(os.path.join(backup_dir, "backup-baseline.json"))


def test_backup_failure_does_not_remove_existing_backups(temp_dir):
    from unittest.mock import patch

    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    db.backup_database(temp_dir)
    backup_dir = os.path.join(temp_dir, "database-backups")
    existing = [f for f in os.listdir(backup_dir) if f.endswith(".zip")]
    assert len(existing) == 1
    with patch.object(db, "_backup_to_zip", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            db.backup_database(temp_dir, max_count=1)
    still_there = [f for f in os.listdir(backup_dir) if f.endswith(".zip")]
    assert len(still_there) == 1


def test_check_db_health_at_open_no_baseline_ok(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    issues = db.check_db_health_at_open(temp_dir)
    assert issues == []


def test_check_db_health_at_open_baseline_suspicious_content(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    db.messages.upsert_lxmf_message(
        {
            "hash": "h1",
            "source_hash": "s",
            "destination_hash": "d",
            "peer_hash": "p",
            "state": "delivered",
            "progress": 1.0,
            "is_incoming": 1,
            "method": "direct",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": "t",
            "content": "c",
            "fields": "{}",
            "timestamp": 0,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
        }
    )
    db.backup_database(temp_dir)
    db.messages.delete_all_lxmf_messages()
    issues = db.check_db_health_at_open(temp_dir)
    assert len(issues) >= 1
    assert any("anomaly" in i.lower() or "messages" in i for i in issues)


def test_check_db_health_at_open_integrity_fail(temp_dir):
    from unittest.mock import patch

    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    with patch.object(db.provider, "integrity_check", return_value=[("corrupt",)]):
        issues = db.check_db_health_at_open(temp_dir)
    assert len(issues) >= 1
    assert any("integrity" in i.lower() for i in issues)


def test_check_db_health_at_close_no_issues(temp_dir):
    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    issues = db.check_db_health_at_close(temp_dir)
    assert issues == []


def test_check_db_health_at_close_integrity_fail(temp_dir):
    from unittest.mock import patch

    db_path = os.path.join(temp_dir, "test.db")
    db = Database(db_path)
    db.initialize()
    with patch.object(db.provider, "integrity_check", return_value=[("corrupt",)]):
        issues = db.check_db_health_at_close(temp_dir)
    assert len(issues) >= 1
    assert any("integrity" in i.lower() for i in issues)


def test_is_backup_suspicious_does_not_mistrigger_empty_baseline():
    from meshchatx.src.backend.database import Database

    db = Database(":memory:")
    db.initialize()
    assert (
        db._is_backup_suspicious({"message_count": 0, "total_bytes": 0}, None) is False
    )
    assert (
        db._is_backup_suspicious({"message_count": 10, "total_bytes": 1000}, None)
        is False
    )


def test_is_backup_suspicious_does_not_mistrigger_legitimate_empty():
    from meshchatx.src.backend.database import Database

    db = Database(":memory:")
    db.initialize()
    baseline = {"message_count": 0, "total_bytes": 5000}
    assert (
        db._is_backup_suspicious({"message_count": 0, "total_bytes": 5000}, baseline)
        is False
    )


def test_is_backup_suspicious_does_not_mistrigger_small_db():
    from meshchatx.src.backend.database import Database

    db = Database(":memory:")
    db.initialize()
    baseline = {"message_count": 5, "total_bytes": 50_000}
    assert (
        db._is_backup_suspicious({"message_count": 5, "total_bytes": 55_000}, baseline)
        is False
    )
