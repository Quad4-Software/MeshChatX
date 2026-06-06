# SPDX-License-Identifier: 0BSD

import sqlite3
import sys
import threading
import weakref

_SQLITE_CONNECT_KW = {}
if sys.version_info >= (3, 14):
    _SQLITE_CONNECT_KW["cached_statements"] = 100

_SQLITE_BUSY_TIMEOUT_MS = 5000


class DatabaseProvider:
    _instance = None
    _lock = threading.RLock()
    _all_locals = weakref.WeakSet()

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._local = threading.local()
        self._all_locals.add(self._local)
        self._memory_connection = None

    @staticmethod
    def _configure_connection(connection):
        if connection is None:
            return
        try:
            connection.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
        except sqlite3.OperationalError:
            pass
        try:
            connection.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass

    @classmethod
    def get_instance(cls, db_path=None):
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    msg = "Database path must be provided for the first initialization"
                    raise ValueError(msg)
                cls._instance = cls(db_path)
            elif db_path is not None and cls._instance.db_path != db_path:
                cls._instance.close_all()
                cls._instance = cls(db_path)
            return cls._instance

    @property
    def connection(self):
        # In-memory databases are private to the connection.
        # If we use threading.local(), each thread gets a DIFFERENT in-memory database.
        # For :memory:, we must share the connection across threads.
        if self.db_path == ":memory:":
            if self._memory_connection is None:
                with self._lock:
                    if self._memory_connection is None:
                        self._memory_connection = sqlite3.connect(
                            self.db_path,
                            check_same_thread=False,
                            isolation_level=None,
                            **_SQLITE_CONNECT_KW,
                        )
                        self._memory_connection.row_factory = sqlite3.Row
                        self._configure_connection(self._memory_connection)
            return self._memory_connection

        if not hasattr(self._local, "connection"):
            # isolation_level=None enables autocommit mode, letting us manage transactions manually
            self._local.connection = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,
                **_SQLITE_CONNECT_KW,
            )
            self._local.connection.row_factory = sqlite3.Row
            if self.db_path != ":memory:":
                self._configure_connection(self._local.connection)
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
        # Default behavior: if we're in a manual transaction, don't commit automatically
        elif not self.connection.in_transaction:
            # In autocommit mode, non-DML statements don't start transactions.
            # DML statements might if they are part of a BEGIN block.
            # Actually, in isolation_level=None, NOTHING starts a transaction unless we say BEGIN.
            pass
        return cursor

    def begin(self):
        try:
            # IMMEDIATE acquires a reserved lock up front so concurrent writers wait
            # on busy_timeout instead of failing with "database is locked" at commit.
            self.connection.execute("BEGIN IMMEDIATE")
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

    def executemany(self, query, params_seq):
        cursor = self.connection.cursor()
        cursor.executemany(query, params_seq)
        return cursor

    def fetchone(self, query, params=None):
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, query, params=None):
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        if self.db_path == ":memory:" and self._memory_connection:
            try:
                self._memory_connection.commit()
                self._memory_connection.close()
            except Exception:
                pass
            self._memory_connection = None

        if hasattr(self._local, "connection"):
            try:
                self.commit()  # Ensure everything is saved
                self._local.connection.close()
            except Exception:
                pass
            del self._local.connection

    def close_all(self):
        with self._lock:
            if self._memory_connection:
                try:
                    self._memory_connection.commit()
                    self._memory_connection.close()
                except Exception:
                    pass
                self._memory_connection = None

            for loc in self._all_locals:
                if hasattr(loc, "connection"):
                    try:
                        loc.connection.commit()
                        loc.connection.close()
                    except Exception:
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
