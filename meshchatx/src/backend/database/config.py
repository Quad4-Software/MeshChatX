# SPDX-License-Identifier: 0BSD

from datetime import UTC, datetime

from .provider import DatabaseProvider


class ConfigDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def get(self, key, default=None):
        row = self.provider.fetchone("SELECT value FROM config WHERE key = ?", (key,))
        if row:
            return row["value"]
        return default

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

    def delete(self, key):
        self.provider.execute("DELETE FROM config WHERE key = ?", (key,))
