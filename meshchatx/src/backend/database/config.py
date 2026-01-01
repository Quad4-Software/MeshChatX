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
            self.provider.execute(
                "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(value), datetime.now(UTC)),
            )

    def delete(self, key):
        self.provider.execute("DELETE FROM config WHERE key = ?", (key,))

