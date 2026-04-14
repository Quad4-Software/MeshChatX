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
            "peer_hash",
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
            "reply_to_hash",
            "attachments_stripped",
        ]

        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        update_set = ", ".join([f"{f} = EXCLUDED.{f}" for f in fields if f != "hash"])

        query = (
            f"INSERT INTO lxmf_messages ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?) "  # noqa: S608
            f"ON CONFLICT(hash) DO UPDATE SET {update_set}, updated_at = EXCLUDED.updated_at"
        )

        params = []
        for f in fields:
            val = data.get(f)
            if f == "fields" and isinstance(val, dict):
                val = json.dumps(val)
            params.append(val)

        now = datetime.now(UTC).isoformat()
        params.append(now)
        params.append(now)

        self.provider.execute(query, params)

    def update_lxmf_message_state(
        self,
        message_hash,
        state,
        progress,
        delivery_attempts,
        next_delivery_attempt_at,
        rssi=None,
        snr=None,
        quality=None,
    ):
        """Lightweight update for delivery-state changes only.

        Avoids re-serializing the full message (including base64 attachment
        data) which the heavy ``upsert_lxmf_message`` path does.
        """
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            "UPDATE lxmf_messages SET state = ?, progress = ?, "
            "delivery_attempts = ?, next_delivery_attempt_at = ?, "
            "rssi = ?, snr = ?, quality = ?, updated_at = ? "
            "WHERE hash = ?",
            (
                state,
                progress,
                delivery_attempts,
                next_delivery_attempt_at,
                rssi,
                snr,
                quality,
                now,
                message_hash,
            ),
        )

    def get_lxmf_message_by_hash(self, message_hash):
        return self.provider.fetchone(
            "SELECT * FROM lxmf_messages WHERE hash = ?",
            (message_hash,),
        )

    def list_message_hashes_for_peer(self, peer_hash):
        rows = self.provider.fetchall(
            "SELECT hash FROM lxmf_messages WHERE peer_hash = ?",
            (peer_hash,),
        )
        return [r["hash"] for r in rows]

    def get_pinned_peer_hashes(self):
        rows = self.provider.fetchall(
            "SELECT peer_hash FROM lxmf_conversation_pins ORDER BY pinned_at DESC",
        )
        return [r["peer_hash"] for r in rows]

    def is_peer_pinned(self, peer_hash):
        row = self.provider.fetchone(
            "SELECT 1 AS ok FROM lxmf_conversation_pins WHERE peer_hash = ?",
            (peer_hash,),
        )
        return row is not None

    def set_peer_pinned(self, peer_hash, pinned):
        if pinned:
            self.provider.execute(
                """
                INSERT INTO lxmf_conversation_pins (peer_hash, pinned_at)
                VALUES (?, strftime('%s', 'now'))
                ON CONFLICT(peer_hash) DO UPDATE SET pinned_at = EXCLUDED.pinned_at
                """,
                (peer_hash,),
            )
        else:
            self.provider.execute(
                "DELETE FROM lxmf_conversation_pins WHERE peer_hash = ?",
                (peer_hash,),
            )

    def toggle_peer_pin(self, peer_hash):
        if self.is_peer_pinned(peer_hash):
            self.set_peer_pinned(peer_hash, False)
            return False
        self.set_peer_pinned(peer_hash, True)
        return True

    def delete_lxmf_messages_by_hashes(self, message_hashes):
        if not message_hashes:
            return
        placeholders = ", ".join(["?"] * len(message_hashes))
        self.provider.execute(
            f"DELETE FROM lxmf_messages WHERE hash IN ({placeholders})",  # noqa: S608
            tuple(message_hashes),
        )

    def delete_lxmf_message_by_hash(self, message_hash):
        self.provider.execute(
            "DELETE FROM lxmf_messages WHERE hash = ?",
            (message_hash,),
        )

    def delete_all_lxmf_messages(self):
        with self.provider:
            self.provider.execute("DELETE FROM lxmf_messages")
            self.provider.execute("DELETE FROM lxmf_conversation_read_state")

    def get_all_lxmf_messages(self, limit=5000, offset=0):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_messages ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def count_lxmf_messages(self):
        row = self.provider.fetchone("SELECT COUNT(*) AS count FROM lxmf_messages")
        return row["count"] if row and row["count"] is not None else 0

    def count_lxmf_messages_by_state(self, state):
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS count FROM lxmf_messages WHERE state = ?",
            (state,),
        )
        return row["count"] if row and row["count"] is not None else 0

    def get_conversation_messages(self, destination_hash, limit=100, offset=0):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_messages WHERE peer_hash = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (destination_hash, limit, offset),
        )

    CONVERSATION_LIST_COLUMNS = (
        "m1.id, m1.hash, m1.source_hash, m1.destination_hash, m1.peer_hash, "
        "m1.state, m1.is_incoming, m1.title, m1.timestamp, m1.created_at, m1.updated_at"
    )

    def get_conversations(self):
        query = f"""
            SELECT {self.CONVERSATION_LIST_COLUMNS} FROM lxmf_messages m1
            INNER JOIN (
                SELECT peer_hash, MAX(timestamp) as max_ts
                FROM lxmf_messages
                WHERE peer_hash IS NOT NULL
                GROUP BY peer_hash
            ) m2 ON m1.peer_hash = m2.peer_hash AND m1.timestamp = m2.max_ts
            GROUP BY m1.peer_hash
            ORDER BY m1.timestamp DESC
        """  # noqa: S608
        return self.provider.fetchall(query)

    def mark_conversation_as_read(self, destination_hash):
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            """
            INSERT INTO lxmf_conversation_read_state (destination_hash, last_read_at, created_at, updated_at) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET 
                last_read_at = EXCLUDED.last_read_at,
                updated_at = EXCLUDED.updated_at
            """,
            (destination_hash, now, now, now),
        )

    def mark_conversations_as_read(self, destination_hashes):
        if not destination_hashes:
            return
        now = datetime.now(UTC).isoformat()
        with self.provider:
            self.provider.executemany(
                """
                INSERT INTO lxmf_conversation_read_state (destination_hash, last_read_at, created_at, updated_at) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(destination_hash) DO UPDATE SET 
                    last_read_at = EXCLUDED.last_read_at,
                    updated_at = EXCLUDED.updated_at
                """,
                [(h, now, now, now) for h in destination_hashes],
            )

    def is_conversation_unread(self, destination_hash):
        row = self.provider.fetchone(
            """
            SELECT m.timestamp, r.last_read_at 
            FROM lxmf_messages m
            LEFT JOIN lxmf_conversation_read_state r ON r.destination_hash = ?
            WHERE m.peer_hash = ? AND m.is_incoming = 1
            ORDER BY m.timestamp DESC LIMIT 1
        """,
            (destination_hash, destination_hash),
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
            "SELECT * FROM lxmf_messages WHERE state = 'failed' AND peer_hash = ? ORDER BY id ASC",
            (destination_hash,),
        )

    def get_failed_messages_count(self, destination_hash):
        row = self.provider.fetchone(
            "SELECT COUNT(*) as count FROM lxmf_messages WHERE state = 'failed' AND peer_hash = ?",
            (destination_hash,),
        )
        return row["count"] if row else 0

    def get_conversations_unread_states(self, destination_hashes):
        if not destination_hashes:
            return {}

        placeholders = ", ".join(["?"] * len(destination_hashes))
        query = f"""
            SELECT peer_hash, MAX(timestamp) as latest_ts, last_read_at
            FROM lxmf_messages m
            LEFT JOIN lxmf_conversation_read_state r ON r.destination_hash = m.peer_hash
            WHERE m.peer_hash IN ({placeholders}) AND m.is_incoming = 1
            GROUP BY m.peer_hash
        """  # noqa: S608
        rows = self.provider.fetchall(query, destination_hashes)

        unread_states = {}
        for row in rows:
            peer_hash = row["peer_hash"]
            latest_ts = row["latest_ts"]
            last_read_at_str = row["last_read_at"]

            if not last_read_at_str:
                unread_states[peer_hash] = True
                continue

            last_read_at = datetime.fromisoformat(last_read_at_str)
            if last_read_at.tzinfo is None:
                last_read_at = last_read_at.replace(tzinfo=UTC)

            unread_states[peer_hash] = latest_ts > last_read_at.timestamp()

        return unread_states

    def get_conversations_failed_counts(self, destination_hashes):
        if not destination_hashes:
            return {}
        placeholders = ", ".join(["?"] * len(destination_hashes))
        rows = self.provider.fetchall(
            f"SELECT peer_hash, COUNT(*) as count FROM lxmf_messages WHERE state = 'failed' AND peer_hash IN ({placeholders}) GROUP BY peer_hash",  # noqa: S608
            tuple(destination_hashes),
        )
        return {row["peer_hash"]: row["count"] for row in rows}

    def get_conversations_attachment_states(self, destination_hashes):
        if not destination_hashes:
            return {}

        placeholders = ", ".join(["?"] * len(destination_hashes))
        query = f"""
            SELECT peer_hash, 1 as has_attachments
            FROM lxmf_messages
            WHERE peer_hash IN ({placeholders})
            AND fields IS NOT NULL AND fields != '{{}}' AND fields != ''
            GROUP BY peer_hash
        """  # noqa: S608
        rows = self.provider.fetchall(query, destination_hashes)

        return {row["peer_hash"]: True for row in rows}

    # Forwarding Mappings
    def get_forwarding_mapping(
        self,
        alias_hash=None,
        original_sender_hash=None,
        final_recipient_hash=None,
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
            """
            INSERT INTO notification_viewed_state (destination_hash, last_viewed_at, created_at, updated_at) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET 
                last_viewed_at = EXCLUDED.last_viewed_at,
                updated_at = EXCLUDED.updated_at
            """,
            (destination_hash, now, now, now),
        )

    def mark_all_notifications_as_viewed(self, destination_hashes=None):
        now = datetime.now(UTC).isoformat()
        if destination_hashes:
            with self.provider:
                self.provider.executemany(
                    """
                    INSERT INTO notification_viewed_state (destination_hash, last_viewed_at, created_at, updated_at) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(destination_hash) DO UPDATE SET 
                        last_viewed_at = EXCLUDED.last_viewed_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [(h, now, now, now) for h in destination_hashes],
                )
        else:
            # mark all conversations as viewed
            self.provider.execute(
                """
                INSERT INTO notification_viewed_state (destination_hash, last_viewed_at, created_at, updated_at)
                SELECT peer_hash, ?, ?, ? FROM lxmf_messages
                WHERE peer_hash IS NOT NULL
                GROUP BY peer_hash
                ON CONFLICT(destination_hash) DO UPDATE SET 
                    last_viewed_at = EXCLUDED.last_viewed_at,
                    updated_at = EXCLUDED.updated_at
                """,
                (now, now, now),
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

    # Folders
    def get_all_folders(self):
        return self.provider.fetchall("SELECT * FROM lxmf_folders ORDER BY name ASC")

    def create_folder(self, name):
        now = datetime.now(UTC).isoformat()
        return self.provider.execute(
            "INSERT INTO lxmf_folders (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name, now, now),
        )

    def rename_folder(self, folder_id, new_name):
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            "UPDATE lxmf_folders SET name = ?, updated_at = ? WHERE id = ?",
            (new_name, now, folder_id),
        )

    def delete_folder(self, folder_id):
        self.provider.execute("DELETE FROM lxmf_folders WHERE id = ?", (folder_id,))

    def get_conversation_folder(self, peer_hash):
        return self.provider.fetchone(
            "SELECT * FROM lxmf_conversation_folders WHERE peer_hash = ?",
            (peer_hash,),
        )

    def move_conversation_to_folder(self, peer_hash, folder_id):
        now = datetime.now(UTC).isoformat()
        if folder_id is None:
            self.provider.execute(
                "DELETE FROM lxmf_conversation_folders WHERE peer_hash = ?",
                (peer_hash,),
            )
        else:
            self.provider.execute(
                """
                INSERT INTO lxmf_conversation_folders (peer_hash, folder_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(peer_hash) DO UPDATE SET
                    folder_id = EXCLUDED.folder_id,
                    updated_at = EXCLUDED.updated_at
                """,
                (peer_hash, folder_id, now, now),
            )

    def move_conversations_to_folder(self, peer_hashes, folder_id):
        if not peer_hashes:
            return
        now = datetime.now(UTC).isoformat()
        with self.provider:
            if folder_id is None:
                placeholders = ", ".join(["?"] * len(peer_hashes))
                self.provider.execute(
                    f"DELETE FROM lxmf_conversation_folders WHERE peer_hash IN ({placeholders})",  # noqa: S608
                    tuple(peer_hashes),
                )
            else:
                self.provider.executemany(
                    """
                    INSERT INTO lxmf_conversation_folders (peer_hash, folder_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(peer_hash) DO UPDATE SET
                        folder_id = EXCLUDED.folder_id,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [(h, folder_id, now, now) for h in peer_hashes],
                )

    def get_all_conversation_folders(self):
        return self.provider.fetchall("SELECT * FROM lxmf_conversation_folders")
