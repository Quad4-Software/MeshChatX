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
            self.provider.execute(
                """
                INSERT INTO config (key, value, created_at, updated_at) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
                """,
                (key, str(value), now, now),
            )

    def delete(self, key):
        self.provider.execute("DELETE FROM config WHERE key = ?", (key,))
