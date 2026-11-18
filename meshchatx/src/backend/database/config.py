# SPDX-License-Identifier: 0BSD

import threading
from datetime import UTC, datetime

from .provider import DatabaseProvider

_MISSING = object()
_ABSENT = object()
_CACHE_MAX_KEYS = 1024


class ConfigDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def _cache_state(self):
        state = getattr(self.provider, "_config_dao_cache", None)
        if not isinstance(state, dict):
            state = {"lock": threading.Lock(), "values": {}}
            self.provider._config_dao_cache = state
        return state

    def get(self, key, default=None):
        state = self._cache_state()
        with state["lock"]:
            value = state["values"].get(key, _MISSING)
            if value is _MISSING:
                row = self.provider.fetchone(
                    "SELECT value FROM config WHERE key = ?", (key,)
                )
                value = row["value"] if row else _ABSENT
                if len(state["values"]) >= _CACHE_MAX_KEYS:
                    state["values"].clear()
                state["values"][key] = value
            return default if value is _ABSENT else value

    def set(self, key, value):
        state = self._cache_state()
        with state["lock"]:
            if value is None:
                self.provider.execute("DELETE FROM config WHERE key = ?", (key,))
                state["values"][key] = _ABSENT
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
                state["values"][key] = value_str

    def delete(self, key):
        state = self._cache_state()
        with state["lock"]:
            self.provider.execute("DELETE FROM config WHERE key = ?", (key,))
            state["values"][key] = _ABSENT
