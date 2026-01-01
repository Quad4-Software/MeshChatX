import sqlite3
import threading


class DatabaseProvider:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path=None):
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    msg = "Database path must be provided for the first initialization"
                    raise ValueError(msg)
                cls._instance = cls(db_path)
            return cls._instance

    @property
    def connection(self):
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    def execute(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()
        return cursor

    def fetchone(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def close(self):
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection

    def vacuum(self):
        self.execute("VACUUM")

    def integrity_check(self):
        return self.fetchall("PRAGMA integrity_check")

    def quick_check(self):
        return self.fetchall("PRAGMA quick_check")

    def checkpoint(self):
        return self.fetchall("PRAGMA wal_checkpoint(TRUNCATE)")

