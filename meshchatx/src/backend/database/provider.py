import sqlite3
import threading
import weakref


class DatabaseProvider:
    _instance = None
    _lock = threading.Lock()
    _all_locals = weakref.WeakSet()

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._local = threading.local()
        self._all_locals.add(self._local)

    @classmethod
    def get_instance(cls, db_path=None):
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    msg = "Database path must be provided for the first initialization"
                    raise ValueError(msg)
                cls._instance = cls(db_path)
            elif db_path is not None and cls._instance.db_path != db_path:
                # If a different path is provided, close the old one and create new
                cls._instance.close()
                cls._instance = cls(db_path)
            return cls._instance

    @property
    def connection(self):
        if not hasattr(self._local, "connection"):
            # isolation_level=None enables autocommit mode, letting us manage transactions manually
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None,
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    def execute(self, query, params=None, commit=None):
        cursor = self.connection.cursor()

        # Convert any datetime objects in params to ISO strings to avoid DeprecationWarning in Python 3.12+
        if params:
            from datetime import datetime

            if isinstance(params, dict):
                params = {
                    k: (v.isoformat() if isinstance(v, datetime) else v)
                    for k, v in params.items()
                }
            else:
                params = tuple(
                    (p.isoformat() if isinstance(p, datetime) else p) for p in params
                )

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # In autocommit mode (isolation_level=None), in_transaction is True
        # only if we explicitly started one with BEGIN and haven't committed/rolled back.
        if commit is True:
            self.connection.commit()
        elif commit is False:
            pass
        else:
            # Default behavior: if we're in a manual transaction, don't commit automatically
            if not self.connection.in_transaction:
                # In autocommit mode, non-DML statements don't start transactions.
                # DML statements might if they are part of a BEGIN block.
                # Actually, in isolation_level=None, NOTHING starts a transaction unless we say BEGIN.
                pass
        return cursor

    def begin(self):
        try:
            self.connection.execute("BEGIN")
        except sqlite3.OperationalError as e:
            if "within a transaction" in str(e):
                pass
            else:
                raise

    def commit(self):
        if self.connection.in_transaction:
            self.connection.commit()

    def rollback(self):
        if self.connection.in_transaction:
            self.connection.rollback()

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()

    def fetchone(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def close(self):
        if hasattr(self._local, "connection"):
            try:
                self.commit()  # Ensure everything is saved
                self._local.connection.close()
            except Exception:  # noqa: S110
                pass
            del self._local.connection

    def close_all(self):
        with self._lock:
            for loc in self._all_locals:
                if hasattr(loc, "connection"):
                    try:
                        loc.connection.commit()
                        loc.connection.close()
                    except Exception:  # noqa: S110
                        pass
                    del loc.connection

    def vacuum(self):
        # VACUUM cannot run inside a transaction
        self.commit()
        self.connection.execute("VACUUM")

    def integrity_check(self):
        return self.fetchall("PRAGMA integrity_check")

    def quick_check(self):
        return self.fetchall("PRAGMA quick_check")

    def checkpoint(self):
        return self.fetchall("PRAGMA wal_checkpoint(TRUNCATE)")
