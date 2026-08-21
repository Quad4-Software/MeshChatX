# SPDX-License-Identifier: 0BSD

import sqlite3
import sys
import threading
import time

_SQLITE_CONNECT_KW = {}
if sys.version_info >= (3, 14):
    _SQLITE_CONNECT_KW["cached_statements"] = 100

_SQLITE_BUSY_TIMEOUT_MS = 5000

# RNS spawns a Thread per announce handler callback. Each callback that
# touches the DB used to pin a WAL connection forever after the thread died.
# Cap retained connections and prune dead-thread owners so FDs cannot grow
# with announce flood (Errno 24 in Docker).
_MAX_CONNECTIONS = 32


class DatabaseProvider:
    _instance = None
    _lock = threading.RLock()

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._local = threading.local()
        # conn -> {"thread_ident": int | None, "last_used": float}
        self._connection_meta: dict[sqlite3.Connection, dict] = {}
        self._close_generation = 0
        self._memory_connection = None
        # Per-connection default. Worker threads opened via asyncio.to_thread
        # never see Database._tune_sqlite_pragmas(), so this must be set here.
        # FILE temp under Landlock often fails with "unable to open database file"
        # when SQLite spills sort/hash work for large conversation queries.
        self.prefer_temp_store_file = False

    @property
    def _connections(self):
        """Compatibility alias for older callers and tests."""
        return self._connection_meta.keys()

    def connection_count(self) -> int:
        with self._lock:
            return len(self._connection_meta)

    def _configure_connection(self, connection):
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
        try:
            if self.prefer_temp_store_file:
                connection.execute("PRAGMA temp_store=FILE")
                connection.execute("PRAGMA cache_size=-2000")
                connection.execute("PRAGMA mmap_size=0")
            else:
                connection.execute("PRAGMA temp_store=MEMORY")
                connection.execute("PRAGMA cache_size=-8000")
                connection.execute("PRAGMA mmap_size=67108864")
        except sqlite3.OperationalError:
            pass
        try:
            connection.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.OperationalError:
            pass

    def _close_tracked_connection(self, conn: sqlite3.Connection) -> None:
        try:
            conn.commit()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        self._connection_meta.pop(conn, None)

    def prune_orphaned_connections(self) -> int:
        """Close connections whose owning thread is no longer alive."""
        with self._lock:
            return self._prune_orphaned_connections_unlocked()

    def _prune_orphaned_connections_unlocked(self) -> int:
        alive = {t.ident for t in threading.enumerate() if t.ident is not None}
        dropped = 0
        for conn, meta in list(self._connection_meta.items()):
            tid = meta.get("thread_ident")
            if tid is None:
                continue
            if tid not in alive:
                self._close_tracked_connection(conn)
                dropped += 1
        return dropped

    def _evict_until_cap_unlocked(
        self, *, keep: sqlite3.Connection | None = None
    ) -> int:
        dropped = 0
        while len(self._connection_meta) >= _MAX_CONNECTIONS:
            candidates = [
                (meta.get("last_used") or 0.0, conn)
                for conn, meta in self._connection_meta.items()
                if conn is not keep
            ]
            if not candidates:
                break
            candidates.sort(key=lambda item: item[0])
            self._close_tracked_connection(candidates[0][1])
            dropped += 1
        return dropped

    def _track_connection(self, conn: sqlite3.Connection) -> None:
        self._connection_meta[conn] = {
            "thread_ident": threading.get_ident(),
            "last_used": time.monotonic(),
        }

    def _touch_connection(self, conn: sqlite3.Connection) -> None:
        meta = self._connection_meta.get(conn)
        if meta is not None:
            meta["last_used"] = time.monotonic()
            meta["thread_ident"] = threading.get_ident()

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

        local_gen = getattr(self._local, "generation", None)
        if (
            not hasattr(self._local, "connection")
            or local_gen != self._close_generation
        ):
            if self.db_path is None:
                msg = "db_path is required for database connections"
                raise ValueError(msg)
            with self._lock:
                local_gen = getattr(self._local, "generation", None)
                if (
                    hasattr(self._local, "connection")
                    and local_gen == self._close_generation
                ):
                    self._touch_connection(self._local.connection)
                    return self._local.connection
                self._prune_orphaned_connections_unlocked()
                self._evict_until_cap_unlocked()
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,
                    check_same_thread=False,
                    isolation_level=None,
                    **_SQLITE_CONNECT_KW,
                )
                conn.row_factory = sqlite3.Row
                self._configure_connection(conn)
                self._local.connection = conn
                self._local.generation = self._close_generation
                self._track_connection(conn)
        else:
            with self._lock:
                self._touch_connection(self._local.connection)
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
            conn = self._local.connection
            try:
                self.commit()
            except Exception:
                pass
            with self._lock:
                self._close_tracked_connection(conn)
            del self._local.connection

    def close_all(self):
        with self._lock:
            self._close_generation += 1
            if self._memory_connection:
                try:
                    self._memory_connection.commit()
                    self._memory_connection.close()
                except Exception:
                    pass
                self._memory_connection = None

            for conn in list(self._connection_meta.keys()):
                self._close_tracked_connection(conn)
            self._connection_meta.clear()
            if hasattr(self._local, "connection"):
                del self._local.connection

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
