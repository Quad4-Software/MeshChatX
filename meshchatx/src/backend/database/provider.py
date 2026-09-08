# SPDX-License-Identifier: 0BSD

import logging
import sqlite3
import sys
import threading
import time
import weakref

from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable

logger = logging.getLogger("meshchatx.database")

_SQLITE_CONNECT_KW = {}
if sys.version_info >= (3, 14):
    _SQLITE_CONNECT_KW["cached_statements"] = 100

_SQLITE_BUSY_TIMEOUT_MS = 5000

# Dead threads and idle live threads are both pruned. Keeping an idle
# connection open for a live thread leaks FDs when RNS/LXMF spawns many
# short-lived workers (GitHub issue 72).
_IDLE_REAP_INTERVAL_SECONDS = 30
_IDLE_CONNECTION_TIMEOUT_SECONDS = 120
_MAX_CONNECTIONS_SOFT = 64


class DatabaseProvider:
    _instance = None
    _lock = threading.RLock()
    _IDLE_REAP_INTERVAL_SECONDS = _IDLE_REAP_INTERVAL_SECONDS
    _IDLE_CONNECTION_TIMEOUT_SECONDS = _IDLE_CONNECTION_TIMEOUT_SECONDS
    _MAX_CONNECTIONS_SOFT = _MAX_CONNECTIONS_SOFT

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._local = threading.local()
        # conn -> {"thread_ident": int | None, "last_used": float, "active_count": int}
        self._connection_meta: dict[sqlite3.Connection, dict] = {}
        self._by_ident: dict[int, sqlite3.Connection] = {}
        self._close_generation = 0
        self._memory_connection = None
        # Per-connection default. Worker threads opened via asyncio.to_thread
        # never see Database._tune_sqlite_pragmas(), so this must be set here.
        # FILE temp under Landlock often fails with "unable to open database file"
        # when SQLite spills sort/hash work for large conversation queries.
        self.prefer_temp_store_file = False
        self._reaper_stop = threading.Event()
        self._reaper_thread: threading.Thread | None = None
        self._start_reaper()

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

    def _connection_usable(self, conn) -> bool:
        if conn is None:
            return False
        if conn not in self._connection_meta:
            return False
        try:
            conn.in_transaction
        except sqlite3.ProgrammingError:
            return False
        except Exception:
            return False
        return True

    def _close_tracked_connection(self, conn: sqlite3.Connection) -> None:
        meta = self._connection_meta.pop(conn, None)
        if meta is not None:
            ident = meta.get("thread_ident")
            if ident is not None and self._by_ident.get(ident) is conn:
                self._by_ident.pop(ident, None)
        try:
            conn.commit()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    def _drop_local_connection(self) -> None:
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            with self._lock:
                self._close_tracked_connection(conn)
        if hasattr(self._local, "connection"):
            del self._local.connection

    def prune_orphaned_connections(self) -> int:
        """Close dead threads' handles and idle live threads' handles."""
        with self._lock:
            return self._prune_connections_unlocked()

    def _prune_orphaned_connections_unlocked(self) -> int:
        alive = {t.ident for t in threading.enumerate() if t.ident is not None}
        dropped = 0
        for ident, conn in list(self._by_ident.items()):
            if ident in alive:
                continue
            self._close_tracked_connection(conn)
            dropped += 1
        # Connections missing from _by_ident (should not happen) still leak FDs.
        for conn, meta in list(self._connection_meta.items()):
            tid = meta.get("thread_ident")
            if tid is None or tid not in alive:
                self._close_tracked_connection(conn)
                dropped += 1
        return dropped

    def _prune_idle_connections_unlocked(self) -> int:
        """Close live threads' connections that have been idle too long.

        Keeps handles with active queries or open transactions. This prevents
        the announce-flood FD growth described in issue 72.
        """
        if self.db_path == ":memory:":
            return 0
        now = time.monotonic()
        timeout = self._IDLE_CONNECTION_TIMEOUT_SECONDS
        dropped = 0
        for conn, meta in list(self._connection_meta.items()):
            if meta.get("active_count", 0) > 0:
                continue
            if not self._connection_usable(conn):
                self._close_tracked_connection(conn)
                dropped += 1
                continue
            if conn.in_transaction:
                continue
            last_used = meta.get("last_used", 0)
            if now - last_used > timeout:
                self._close_tracked_connection(conn)
                dropped += 1
        return dropped

    def _prune_connections_unlocked(self) -> int:
        """Close dead and idle connections before opening a new handle."""
        return (
            self._prune_orphaned_connections_unlocked()
            + self._prune_idle_connections_unlocked()
        )

    def _start_reaper(self) -> None:
        if self._IDLE_CONNECTION_TIMEOUT_SECONDS <= 0:
            return
        weak_self = weakref.ref(self)
        self._reaper_thread = threading.Thread(
            target=self._reaper_loop,
            args=(weak_self, self._reaper_stop),
            name="meshchatx-db-reaper",
            daemon=True,
        )
        self._reaper_thread.start()

    def _stop_reaper(self) -> None:
        if self._reaper_thread is None:
            return
        self._reaper_stop.set()
        self._reaper_thread.join(timeout=1.0)
        self._reaper_thread = None

    @staticmethod
    def _reaper_loop(weak_self, stop_event) -> None:
        while True:
            provider = weak_self()
            if provider is None:
                return
            interval = provider._IDLE_REAP_INTERVAL_SECONDS
            if stop_event.wait(interval):
                return
            provider = weak_self()
            if provider is None:
                return
            try:
                with provider._lock:
                    provider._prune_connections_unlocked()
            except Exception:
                logger.debug("Database connection reaper failed", exc_info=True)

    def _track_connection(self, conn: sqlite3.Connection) -> None:
        ident = threading.get_ident()
        old = self._by_ident.get(ident)
        if old is not None and old is not conn:
            self._close_tracked_connection(old)
        self._by_ident[ident] = conn
        self._connection_meta[conn] = {
            "thread_ident": ident,
            "last_used": time.monotonic(),
            "active_count": 0,
        }

    def _touch_connection(self, conn: sqlite3.Connection) -> None:
        meta = self._connection_meta.get(conn)
        if meta is not None:
            meta["last_used"] = time.monotonic()
            meta["thread_ident"] = threading.get_ident()

    def _set_active(self, conn: sqlite3.Connection, delta: int) -> None:
        meta = self._connection_meta.get(conn)
        if meta is None:
            return
        count = meta.get("active_count", 0) + delta
        meta["active_count"] = max(0, count)

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

    def _open_file_connection(self) -> sqlite3.Connection:
        if self.db_path is None:
            msg = "db_path is required for database connections"
            raise ValueError(msg)
        self._prune_orphaned_connections_unlocked()
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
        if len(self._connection_meta) > self._MAX_CONNECTIONS_SOFT:
            logger.warning(
                "SQLite connection count %s exceeds %s live-thread handles",
                len(self._connection_meta),
                self._MAX_CONNECTIONS_SOFT,
            )
        return conn

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
        local_conn = getattr(self._local, "connection", None)
        if local_conn is not None and local_gen == self._close_generation:
            with self._lock:
                if self._connection_usable(local_conn):
                    self._touch_connection(local_conn)
                    return local_conn
                self._close_tracked_connection(local_conn)
            if hasattr(self._local, "connection"):
                del self._local.connection

        with self._lock:
            local_gen = getattr(self._local, "generation", None)
            local_conn = getattr(self._local, "connection", None)
            if (
                local_conn is not None
                and local_gen == self._close_generation
                and self._connection_usable(local_conn)
            ):
                self._touch_connection(local_conn)
                return local_conn
            return self._open_file_connection()

    def _call_with_reconnect(self, fn):
        try:
            return fn()
        except (sqlite3.ProgrammingError, sqlite3.OperationalError) as exc:
            if not sqlite_error_is_retryable(exc):
                raise
            self._drop_local_connection()
            return fn()

    def execute(self, query, params=None, commit=None):
        def _run():
            conn = self.connection
            self._set_active(conn, 1)
            try:
                cursor = conn.cursor()

                # Convert any datetime objects in params to ISO strings to avoid DeprecationWarning in Python 3.12+
                if params:
                    from datetime import datetime

                    if isinstance(params, dict):
                        bound = {
                            k: (v.isoformat() if isinstance(v, datetime) else v)
                            for k, v in params.items()
                        }
                    else:
                        bound = tuple(
                            (p.isoformat() if isinstance(p, datetime) else p)
                            for p in params
                        )
                else:
                    bound = None

                if bound:
                    cursor.execute(query, bound)
                else:
                    cursor.execute(query)

                # In autocommit mode (isolation_level=None), in_transaction is True
                # only if we explicitly started one with BEGIN and haven't committed/rolled back.
                if commit is True:
                    conn.commit()
                elif commit is False:
                    pass
                # Default behavior: if we're in a manual transaction, don't commit automatically
                elif not conn.in_transaction:
                    # In autocommit mode, non-DML statements don't start transactions.
                    # DML statements might if they are part of a BEGIN block.
                    # Actually, in isolation_level=None, NOTHING starts a transaction unless we say BEGIN.
                    pass
                return cursor
            finally:
                self._set_active(conn, -1)
                self._touch_connection(conn)

        return self._call_with_reconnect(_run)

    def begin(self):
        def _run():
            try:
                # IMMEDIATE acquires a reserved lock up front so concurrent writers wait
                # on busy_timeout instead of failing with "database is locked" at commit.
                self.connection.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as e:
                if "within a transaction" in str(e):
                    pass
                else:
                    raise

        self._call_with_reconnect(_run)

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
        def _run():
            conn = self.connection
            self._set_active(conn, 1)
            try:
                cursor = conn.cursor()
                cursor.executemany(query, params_seq)
                return cursor
            finally:
                self._set_active(conn, -1)
                self._touch_connection(conn)

        return self._call_with_reconnect(_run)

    def fetchone(self, query, params=None):
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, query, params=None):
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self._stop_reaper()
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
        self._stop_reaper()
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
            self._by_ident.clear()
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
