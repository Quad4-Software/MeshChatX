import sqlite3
import threading

import pytest

from meshchatx.src.backend.database.provider import DatabaseProvider


def test_database_provider_memory():
    provider = DatabaseProvider(":memory:")
    conn = provider.connection
    assert isinstance(conn, sqlite3.Connection)
    assert provider.db_path == ":memory:"

    # Same connection for all threads in memory mode
    def get_conn():
        assert provider.connection == conn

    t = threading.Thread(target=get_conn)
    t.start()
    t.join()


def test_database_provider_execute(tmp_path):
    db_file = tmp_path / "test.db"
    provider = DatabaseProvider(str(db_file))

    provider.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
    provider.execute("INSERT INTO test (val) VALUES (?)", ("hello",))

    row = provider.fetchone("SELECT val FROM test")
    assert row["val"] == "hello"


def test_database_provider_transactions(tmp_path):
    db_file = tmp_path / "test.db"
    provider = DatabaseProvider(str(db_file))
    provider.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")

    provider.begin()
    provider.execute("INSERT INTO test (val) VALUES (?)", ("tx1",))
    provider.rollback()

    assert provider.fetchone("SELECT COUNT(*) as count FROM test")["count"] == 0

    provider.begin()
    provider.execute("INSERT INTO test (val) VALUES (?)", ("tx2",))
    provider.commit()
    assert provider.fetchone("SELECT COUNT(*) as count FROM test")["count"] == 1


def test_database_provider_singleton():
    # Reset singleton for test
    DatabaseProvider._instance = None
    p1 = DatabaseProvider.get_instance(":memory:")
    p2 = DatabaseProvider.get_instance()
    assert p1 == p2

    with pytest.raises(ValueError, match="Database path must be provided"):
        DatabaseProvider._instance = None
        DatabaseProvider.get_instance()
