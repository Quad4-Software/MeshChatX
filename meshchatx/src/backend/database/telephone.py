from .provider import DatabaseProvider


class TelephoneDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def add_call_history(
        self,
        remote_identity_hash,
        remote_identity_name,
        is_incoming,
        status,
        duration_seconds,
        timestamp,
    ):
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO call_history (
                remote_identity_hash,
                remote_identity_name,
                is_incoming,
                status,
                duration_seconds,
                timestamp,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                remote_identity_hash,
                remote_identity_name,
                1 if is_incoming else 0,
                status,
                duration_seconds,
                timestamp,
                now,
            ),
        )

    def get_call_history(self, limit=10):
        return self.provider.fetchall(
            "SELECT * FROM call_history ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
