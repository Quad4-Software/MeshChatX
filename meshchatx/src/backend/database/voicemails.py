from .provider import DatabaseProvider


class VoicemailDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def add_voicemail(
        self,
        remote_identity_hash,
        remote_identity_name,
        filename,
        duration_seconds,
        timestamp,
    ):
        self.provider.execute(
            """
            INSERT INTO voicemails (
                remote_identity_hash,
                remote_identity_name,
                filename,
                duration_seconds,
                timestamp
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                remote_identity_hash,
                remote_identity_name,
                filename,
                duration_seconds,
                timestamp,
            ),
        )

    def get_voicemails(self, limit=50, offset=0):
        return self.provider.fetchall(
            "SELECT * FROM voicemails ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def get_voicemail(self, voicemail_id):
        return self.provider.fetchone(
            "SELECT * FROM voicemails WHERE id = ?",
            (voicemail_id,),
        )

    def mark_as_read(self, voicemail_id):
        self.provider.execute(
            "UPDATE voicemails SET is_read = 1 WHERE id = ?",
            (voicemail_id,),
        )

    def delete_voicemail(self, voicemail_id):
        self.provider.execute(
            "DELETE FROM voicemails WHERE id = ?",
            (voicemail_id,),
        )

    def get_unread_count(self):
        row = self.provider.fetchone(
            "SELECT COUNT(*) as count FROM voicemails WHERE is_read = 0"
        )
        return row["count"] if row else 0
