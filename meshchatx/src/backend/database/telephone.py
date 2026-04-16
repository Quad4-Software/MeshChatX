# SPDX-License-Identifier: 0BSD

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

    def get_call_history(self, search=None, limit=10, offset=0):
        if search:
            return self.provider.fetchall(
                """
                SELECT * FROM call_history 
                WHERE remote_identity_name LIKE ? OR remote_identity_hash LIKE ? 
                ORDER BY timestamp DESC LIMIT ? OFFSET ?
                """,
                (f"%{search}%", f"%{search}%", limit, offset),
            )
        return self.provider.fetchall(
            "SELECT * FROM call_history ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def clear_call_history(self):
        self.provider.execute("DELETE FROM call_history")

    def add_call_recording(
        self,
        remote_identity_hash,
        remote_identity_name,
        filename_rx,
        filename_tx,
        duration_seconds,
        timestamp,
    ):
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO call_recordings (
                remote_identity_hash,
                remote_identity_name,
                filename_rx,
                filename_tx,
                duration_seconds,
                timestamp,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                remote_identity_hash,
                remote_identity_name,
                filename_rx,
                filename_tx,
                duration_seconds,
                timestamp,
                now,
            ),
        )

    def get_call_recordings(self, search=None, limit=10, offset=0):
        if search:
            return self.provider.fetchall(
                """
                SELECT * FROM call_recordings 
                WHERE remote_identity_name LIKE ? OR remote_identity_hash LIKE ? 
                ORDER BY timestamp DESC LIMIT ? OFFSET ?
                """,
                (f"%{search}%", f"%{search}%", limit, offset),
            )
        return self.provider.fetchall(
            "SELECT * FROM call_recordings ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def get_call_recording(self, recording_id):
        return self.provider.fetchone(
            "SELECT * FROM call_recordings WHERE id = ?",
            (recording_id,),
        )

    def delete_call_recording(self, recording_id):
        self.provider.execute(
            "DELETE FROM call_recordings WHERE id = ?",
            (recording_id,),
        )
