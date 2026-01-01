import json
from datetime import UTC, datetime

from .provider import DatabaseProvider


class MessageDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def upsert_lxmf_message(self, data):
        # Ensure data is a dict if it's a sqlite3.Row
        if not isinstance(data, dict):
            data = dict(data)

        # Ensure all required fields are present and handle defaults
        fields = [
            "hash",
            "source_hash",
            "destination_hash",
            "state",
            "progress",
            "is_incoming",
            "method",
            "delivery_attempts",
            "next_delivery_attempt_at",
            "title",
            "content",
            "fields",
            "timestamp",
            "rssi",
            "snr",
            "quality",
            "is_spam",
        ]

        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        update_set = ", ".join([f"{f} = EXCLUDED.{f}" for f in fields if f != "hash"])

        query = (
            f"INSERT INTO lxmf_messages ({columns}, updated_at) VALUES ({placeholders}, ?) "
            f"ON CONFLICT(hash) DO UPDATE SET {update_set}, updated_at = EXCLUDED.updated_at"
        )  # noqa: S608

        params = []
        for f in fields:
            val = data.get(f)
            if f == "fields" and isinstance(val, dict):
                val = json.dumps(val)
            params.append(val)
        params.append(datetime.now(UTC).isoformat())

        self.provider.execute(query, params)

    def get_lxmf_message_by_hash(self, message_hash):
        return self.provider.fetchone(
            "SELECT * FROM lxmf_messages WHERE hash = ?", (message_hash,)
        )

    def delete_lxmf_message_by_hash(self, message_hash):
        self.provider.execute(
            "DELETE FROM lxmf_messages WHERE hash = ?", (message_hash,)
        )

    def get_conversation_messages(self, destination_hash, limit=100, offset=0):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_messages WHERE destination_hash = ? OR source_hash = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (destination_hash, destination_hash, limit, offset),
        )

    def get_conversations(self):
        # This is a bit complex in raw SQL, we need the latest message for each destination
        query = """
            SELECT m1.* FROM lxmf_messages m1
            JOIN (
                SELECT 
                    CASE WHEN is_incoming = 1 THEN source_hash ELSE destination_hash END as peer_hash,
                    MAX(timestamp) as max_ts
                FROM lxmf_messages
                GROUP BY peer_hash
            ) m2 ON (CASE WHEN m1.is_incoming = 1 THEN m1.source_hash ELSE m1.destination_hash END = m2.peer_hash 
                     AND m1.timestamp = m2.max_ts)
            ORDER BY m1.timestamp DESC
        """
        return self.provider.fetchall(query)

    def mark_conversation_as_read(self, destination_hash):
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            "INSERT OR REPLACE INTO lxmf_conversation_read_state (destination_hash, last_read_at, updated_at) VALUES (?, ?, ?)",
            (destination_hash, now, now),
        )

    def is_conversation_unread(self, destination_hash):
        row = self.provider.fetchone(
            """
            SELECT m.timestamp, r.last_read_at 
            FROM lxmf_messages m
            LEFT JOIN lxmf_conversation_read_state r ON r.destination_hash = ?
            WHERE (m.destination_hash = ? OR m.source_hash = ?)
            ORDER BY m.timestamp DESC LIMIT 1
        """,
            (destination_hash, destination_hash, destination_hash),
        )

        if not row:
            return False
        if not row["last_read_at"]:
            return True

        last_read_at = datetime.fromisoformat(row["last_read_at"])
        if last_read_at.tzinfo is None:
            last_read_at = last_read_at.replace(tzinfo=UTC)

        return row["timestamp"] > last_read_at.timestamp()

    def mark_stuck_messages_as_failed(self):
        self.provider.execute(
            """
            UPDATE lxmf_messages 
            SET state = 'failed', updated_at = ?
            WHERE state = 'outbound' 
            OR (state = 'sent' AND method = 'opportunistic') 
            OR state = 'sending'
        """,
            (datetime.now(UTC).isoformat(),),
        )

    def get_failed_messages_for_destination(self, destination_hash):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_messages WHERE state = 'failed' AND destination_hash = ? ORDER BY id ASC",
            (destination_hash,),
        )

    def get_failed_messages_count(self, destination_hash):
        row = self.provider.fetchone(
            "SELECT COUNT(*) as count FROM lxmf_messages WHERE state = 'failed' AND destination_hash = ?",
            (destination_hash,),
        )
        return row["count"] if row else 0

    # Forwarding Mappings
    def get_forwarding_mapping(
        self, alias_hash=None, original_sender_hash=None, final_recipient_hash=None
    ):
        if alias_hash:
            return self.provider.fetchone(
                "SELECT * FROM lxmf_forwarding_mappings WHERE alias_hash = ?",
                (alias_hash,),
            )
        if original_sender_hash and final_recipient_hash:
            return self.provider.fetchone(
                "SELECT * FROM lxmf_forwarding_mappings WHERE original_sender_hash = ? AND final_recipient_hash = ?",
                (original_sender_hash, final_recipient_hash),
            )
        return None

    def create_forwarding_mapping(self, data):
        # Ensure data is a dict if it's a sqlite3.Row
        if not isinstance(data, dict):
            data = dict(data)

        fields = [
            "alias_identity_private_key",
            "alias_hash",
            "original_sender_hash",
            "final_recipient_hash",
            "original_destination_hash",
        ]
        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        query = f"INSERT INTO lxmf_forwarding_mappings ({columns}, created_at) VALUES ({placeholders}, ?)"  # noqa: S608
        params = [data.get(f) for f in fields]
        params.append(datetime.now(UTC).isoformat())
        self.provider.execute(query, params)

    def get_all_forwarding_mappings(self):
        return self.provider.fetchall("SELECT * FROM lxmf_forwarding_mappings")

    def mark_notification_as_viewed(self, destination_hash):
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            "INSERT OR REPLACE INTO notification_viewed_state (destination_hash, last_viewed_at, updated_at) VALUES (?, ?, ?)",
            (destination_hash, now, now),
        )

    def mark_all_notifications_as_viewed(self, destination_hashes):
        now = datetime.now(UTC).isoformat()
        for destination_hash in destination_hashes:
            self.provider.execute(
                "INSERT OR REPLACE INTO notification_viewed_state (destination_hash, last_viewed_at, updated_at) VALUES (?, ?, ?)",
                (destination_hash, now, now),
            )

    def is_notification_viewed(self, destination_hash, message_timestamp):
        row = self.provider.fetchone(
            "SELECT last_viewed_at FROM notification_viewed_state WHERE destination_hash = ?",
            (destination_hash,),
        )
        if not row or not row["last_viewed_at"]:
            return False

        last_viewed_at = datetime.fromisoformat(row["last_viewed_at"])
        if last_viewed_at.tzinfo is None:
            last_viewed_at = last_viewed_at.replace(tzinfo=UTC)

        return message_timestamp <= last_viewed_at.timestamp()
