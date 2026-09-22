# SPDX-License-Identifier: 0BSD

import threading
from datetime import UTC, datetime

from .provider import DatabaseProvider

_MISS = object()
_NO_ROW = object()


class ConfigDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider
        # Config reads dominate hot paths (per-request middleware, websocket
        # connect broadcasts), so each key is cached after its first read.
        # Writes go through set/delete which invalidate the key. Keys written
        # by non-DAO paths (schema seeding, favourites layout) are not read
        # through this DAO, and a database restore creates a new DAO instance.
        self._cache: dict = {}
        self._cache_lock = threading.Lock()

    def get(self, key, default=None):
        with self._cache_lock:
            cached = self._cache.get(key, _MISS)
            if cached is not _MISS:
                return default if cached is _NO_ROW else cached
        row = self.provider.fetchone("SELECT value FROM config WHERE key = ?", (key,))
        with self._cache_lock:
            self._cache[key] = row["value"] if row else _NO_ROW
        return row["value"] if row else default

    def set(self, key, value):
        if value is None:
            self.provider.execute("DELETE FROM config WHERE key = ?", (key,))
        else:
            now = datetime.now(UTC)

            # handle booleans specifically to ensure they are stored as "true"/"false"
            if isinstance(value, bool):
                value_str = "true" if value else "false"
            else:
                value_str = str(value)

            self.provider.execute(
                """
                INSERT INTO config (key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
                """,
                (key, value_str, now, now),
            )
        with self._cache_lock:
            self._cache.pop(key, None)

    def delete(self, key):
        self.provider.execute("DELETE FROM config WHERE key = ?", (key,))
        with self._cache_lock:
            self._cache.pop(key, None)

    def invalidate_cache(self):
        with self._cache_lock:
            self._cache.clear()
