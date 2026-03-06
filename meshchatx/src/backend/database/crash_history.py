import json

from .provider import DatabaseProvider


class CrashHistoryDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def insert_crash(
        self,
        timestamp,
        error_type,
        error_message,
        diagnosed_cause,
        symptoms,
        probability,
        entropy,
        divergence,
    ):
        self.provider.execute(
            """
            INSERT INTO crash_history
                (timestamp, error_type, error_message, diagnosed_cause,
                 symptoms, probability, entropy, divergence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                error_type,
                error_message[:500] if error_message else None,
                diagnosed_cause,
                json.dumps(symptoms) if isinstance(symptoms, dict) else symptoms,
                probability,
                entropy,
                divergence,
            ),
        )

    def get_recent_crashes(self, limit=50):
        return self.provider.fetchall(
            "SELECT * FROM crash_history ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )

    def get_cause_frequencies(self, limit=50):
        return self.provider.fetchall(
            """
            SELECT diagnosed_cause, COUNT(*) as count
            FROM (SELECT * FROM crash_history ORDER BY timestamp DESC LIMIT ?)
            GROUP BY diagnosed_cause
            ORDER BY count DESC
            """,
            (limit,),
        )

    def cleanup_old(self, max_entries=200):
        self.provider.execute(
            """
            DELETE FROM crash_history WHERE id NOT IN (
                SELECT id FROM crash_history ORDER BY timestamp DESC LIMIT ?
            )
            """,
            (max_entries,),
        )
