# SPDX-License-Identifier: 0BSD

import json
from datetime import UTC, datetime

from .provider import DatabaseProvider

_LXMF_UPSERT_FIELDS = (
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
    "fields_meta",
    "has_image",
    "has_audio",
    "has_files",
    "has_reaction",
    "has_telemetry",
    "timestamp",
    "rssi",
    "snr",
    "quality",
    "is_spam",
    "reply_to_hash",
    "attachments_stripped",
    "path_hops_at_send",
    "path_interface_at_send",
    "path_finding_measure",
    "path_row_hash_hex",
)
_LXMF_OPTIONAL_UPSERT_FIELDS = frozenset(
    {
        "attachments_stripped",
        "fields_meta",
        "has_image",
        "has_audio",
        "has_files",
        "has_reaction",
        "has_telemetry",
    },
)
_LXMF_EXPORT_ONLY_KEYS = frozenset({"id", "lxmf_icon"})
_LXMF_ATTACHMENT_FLAG_KEYS = (
    "has_image",
    "has_audio",
    "has_files",
    "has_reaction",
    "has_telemetry",
)


class MessageDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider
        self._lxmf_columns_cache = None
        self._lxmf_upsert_fields_cache = None

    def _lxmf_table_columns(self):
        if self._lxmf_columns_cache is None:
            rows = self.provider.fetchall("PRAGMA table_info(lxmf_messages)")
            self._lxmf_columns_cache = {row["name"] for row in rows}
        return self._lxmf_columns_cache

    def _lxmf_upsert_field_names(self):
        if self._lxmf_upsert_fields_cache is None:
            columns = self._lxmf_table_columns()
            self._lxmf_upsert_fields_cache = [
                field
                for field in _LXMF_UPSERT_FIELDS
                if field in columns or field not in _LXMF_OPTIONAL_UPSERT_FIELDS
            ]
        return self._lxmf_upsert_fields_cache

    @staticmethod
    def normalize_lxmf_message_for_import(data):
        if not isinstance(data, dict):
            data = dict(data)

        row = {
            key: value
            for key, value in data.items()
            if key not in _LXMF_EXPORT_ONLY_KEYS
        }

        message_hash = row.get("hash")
        if not message_hash or not isinstance(message_hash, str):
            return None

        source_hash = row.get("source_hash")
        destination_hash = row.get("destination_hash")
        if not source_hash or not destination_hash:
            return None

        if not row.get("peer_hash"):
            is_incoming = row.get("is_incoming")
            row["peer_hash"] = (
                source_hash if is_incoming in (1, True, "1") else destination_hash
            )

        fields_value = row.get("fields")
        if isinstance(fields_value, dict):
            row["fields"] = json.dumps(fields_value)
        elif isinstance(fields_value, str):
            stripped = fields_value.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        row["fields"] = json.dumps(parsed)
                except json.JSONDecodeError:
                    pass

        for key in (
            "is_incoming",
            "is_spam",
            "attachments_stripped",
            *_LXMF_ATTACHMENT_FLAG_KEYS,
        ):
            if key in row and isinstance(row[key], bool):
                row[key] = int(row[key])

        if row.get("progress") is None:
            row["progress"] = 0.0

        return row

    @staticmethod
    def _enrich_lxmf_message_list_cache(data: dict) -> dict:
        """Fill fields_meta and has_* so list/thread APIs avoid reading fields blobs."""
        from meshchatx.src.backend.lxmf_utils import (
            lxmf_fields_attachment_flags,
            lxmf_fields_without_attachment_bytes,
        )

        fields_value = data.get("fields")
        fields_dict = None
        if isinstance(fields_value, dict):
            fields_dict = fields_value
        elif isinstance(fields_value, str) and fields_value.strip():
            try:
                parsed = json.loads(fields_value)
                if isinstance(parsed, dict):
                    fields_dict = parsed
            except json.JSONDecodeError:
                fields_dict = None

        if fields_dict is None:
            fields_dict = {}

        flags = lxmf_fields_attachment_flags(fields_dict)
        for key, value in flags.items():
            if data.get(key) is None:
                data[key] = value

        if not data.get("fields_meta"):
            data["fields_meta"] = json.dumps(
                lxmf_fields_without_attachment_bytes(fields_dict),
            )

        return data

    def import_lxmf_messages(self, messages):
        imported = 0
        skipped = 0
        errors = []

        if not isinstance(messages, list):
            raise ValueError("messages must be an array")

        for index, message in enumerate(messages):
            normalized = self.normalize_lxmf_message_for_import(message)
            if normalized is None:
                skipped += 1
                continue
            try:
                self.upsert_lxmf_message(normalized)
                imported += 1
            except Exception as exc:
                errors.append(
                    {
                        "index": index,
                        "hash": normalized.get("hash"),
                        "error": str(exc),
                    },
                )

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }

    def upsert_lxmf_message(self, data):
        # Ensure data is a dict if it's a sqlite3.Row
        if not isinstance(data, dict):
            data = dict(data)

        data = self._enrich_lxmf_message_list_cache(data)

        fields = self._lxmf_upsert_field_names()

        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        update_fields = [
            f
            for f in fields
            if f != "hash"
            and f
            not in (
                "timestamp",
                "created_at",
                "path_hops_at_send",
                "path_interface_at_send",
                "path_finding_measure",
                "path_row_hash_hex",
            )
        ]
        update_set = ", ".join([f"{f} = EXCLUDED.{f}" for f in update_fields])

        query = (
            f"INSERT INTO lxmf_messages ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?) "
            f"ON CONFLICT(hash) DO UPDATE SET {update_set}, updated_at = EXCLUDED.updated_at"
        )

        params = []
        for field in fields:
            val = data.get(field)
            if field in ("fields", "fields_meta") and isinstance(val, dict):
                val = json.dumps(val)
            params.append(val)

        now = datetime.now(UTC).isoformat()
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        if not isinstance(created_at, str) or not created_at.strip():
            created_at = now
        if not isinstance(updated_at, str) or not updated_at.strip():
            updated_at = now
        params.append(created_at)
        params.append(updated_at)

        self.provider.execute(query, params)
        peer_hash = data.get("peer_hash")
        if isinstance(peer_hash, str) and peer_hash.strip():
            self.refresh_conversation_summary(peer_hash.strip())

    def refresh_conversation_summary(self, peer_hash):
        """Rebuild the materialized list row for one peer.

        Conversation list queries read lxmf_conversation_summaries so they do
        not GROUP BY the full messages table on every refresh.
        """
        if not peer_hash or not isinstance(peer_hash, str):
            return
        peer_hash = peer_hash.strip()
        if not peer_hash:
            return
        row = self.provider.fetchone(
            """
            SELECT
                id, hash, source_hash, destination_hash, peer_hash, state, progress,
                is_incoming, title,
                substr(COALESCE(content, ''), 1, 240) AS content_preview,
                timestamp, is_spam, reply_to_hash, created_at, updated_at,
                COALESCE(has_image, 0) AS has_image,
                COALESCE(has_audio, 0) AS has_audio,
                COALESCE(has_files, 0) AS has_files,
                COALESCE(has_reaction, 0) AS has_reaction,
                COALESCE(has_telemetry, 0) AS has_telemetry
            FROM lxmf_messages
            WHERE peer_hash = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (peer_hash,),
        )
        if not row:
            self.provider.execute(
                "DELETE FROM lxmf_conversation_summaries WHERE peer_hash = ?",
                (peer_hash,),
            )
            return
        failed_row = self.provider.fetchone(
            """
            SELECT COUNT(*) AS failed_count
            FROM lxmf_messages
            WHERE peer_hash = ? AND state = 'failed'
            """,
            (peer_hash,),
        )
        failed_count = int(failed_row["failed_count"] or 0) if failed_row else 0
        self.provider.execute(
            """
            INSERT INTO lxmf_conversation_summaries (
                peer_hash, latest_message_id, latest_message_hash,
                source_hash, destination_hash, state, progress, is_incoming,
                title, content_preview, timestamp, is_spam, reply_to_hash,
                created_at, updated_at,
                has_image, has_audio, has_files, has_reaction, has_telemetry,
                failed_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(peer_hash) DO UPDATE SET
                latest_message_id = EXCLUDED.latest_message_id,
                latest_message_hash = EXCLUDED.latest_message_hash,
                source_hash = EXCLUDED.source_hash,
                destination_hash = EXCLUDED.destination_hash,
                state = EXCLUDED.state,
                progress = EXCLUDED.progress,
                is_incoming = EXCLUDED.is_incoming,
                title = EXCLUDED.title,
                content_preview = EXCLUDED.content_preview,
                timestamp = EXCLUDED.timestamp,
                is_spam = EXCLUDED.is_spam,
                reply_to_hash = EXCLUDED.reply_to_hash,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                has_image = EXCLUDED.has_image,
                has_audio = EXCLUDED.has_audio,
                has_files = EXCLUDED.has_files,
                has_reaction = EXCLUDED.has_reaction,
                has_telemetry = EXCLUDED.has_telemetry,
                failed_count = EXCLUDED.failed_count
            """,
            (
                peer_hash,
                row["id"],
                row["hash"],
                row["source_hash"],
                row["destination_hash"],
                row["state"],
                row["progress"],
                row["is_incoming"],
                row["title"],
                row["content_preview"],
                row["timestamp"],
                row["is_spam"],
                row["reply_to_hash"],
                row["created_at"],
                row["updated_at"],
                row["has_image"],
                row["has_audio"],
                row["has_files"],
                row["has_reaction"],
                row["has_telemetry"],
                failed_count,
            ),
        )

    def refresh_conversation_summaries_for_peers(self, peer_hashes):
        seen = set()
        for peer_hash in peer_hashes or []:
            if not isinstance(peer_hash, str):
                continue
            key = peer_hash.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            self.refresh_conversation_summary(key)

    def delete_conversation_summary(self, peer_hash):
        if not peer_hash or not isinstance(peer_hash, str):
            return
        self.provider.execute(
            "DELETE FROM lxmf_conversation_summaries WHERE peer_hash = ?",
            (peer_hash.strip(),),
        )

    def set_lxmf_message_path_at_send_if_unset(
        self,
        message_hash,
        hops,
        interface_name,
    ):
        """Store Reticulum path snapshot once (send or receive); never overwrites."""
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            "UPDATE lxmf_messages SET path_hops_at_send = ?, path_interface_at_send = ?, updated_at = ? "
            "WHERE hash = ? AND path_hops_at_send IS NULL",
            (hops, interface_name, now, message_hash),
        )

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
        method=None,
    ):
        """Lightweight update for delivery-state changes only.

        Avoids re-serializing the full message (including base64 attachment
        data) which the heavy upsert_lxmf_message path does.
        """
        now = datetime.now(UTC).isoformat()
        if method is None:
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
        else:
            self.provider.execute(
                "UPDATE lxmf_messages SET state = ?, progress = ?, "
                "delivery_attempts = ?, next_delivery_attempt_at = ?, "
                "rssi = ?, snr = ?, quality = ?, method = ?, updated_at = ? "
                "WHERE hash = ?",
                (
                    state,
                    progress,
                    delivery_attempts,
                    next_delivery_attempt_at,
                    rssi,
                    snr,
                    quality,
                    method,
                    now,
                    message_hash,
                ),
            )
        row = self.provider.fetchone(
            "SELECT peer_hash FROM lxmf_messages WHERE hash = ?",
            (message_hash,),
        )
        if row and row.get("peer_hash"):
            self.refresh_conversation_summary(row["peer_hash"])

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

    def list_message_hashes_with_timestamp_before(self, cutoff_ts: float) -> list[str]:
        rows = self.provider.fetchall(
            "SELECT hash FROM lxmf_messages WHERE timestamp IS NOT NULL AND timestamp < ?",
            (cutoff_ts,),
        )
        return [r["hash"] for r in rows if r.get("hash")]

    def count_lxmf_messages_with_timestamp_before(self, cutoff_ts: float) -> int:
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS count FROM lxmf_messages "
            "WHERE timestamp IS NOT NULL AND timestamp < ?",
            (cutoff_ts,),
        )
        return int(row["count"]) if row and row["count"] is not None else 0

    def get_lxmf_messages_with_timestamp_before(
        self,
        cutoff_ts: float,
        limit: int = 5000,
        offset: int = 0,
    ):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_messages "
            "WHERE timestamp IS NOT NULL AND timestamp < ? "
            "ORDER BY id LIMIT ? OFFSET ?",
            (cutoff_ts, limit, offset),
        )

    def prune_conversation_metadata_for_peers_with_no_messages(self) -> None:
        self.provider.execute(
            """
            DELETE FROM lxmf_conversation_read_state
            WHERE destination_hash NOT IN (
                SELECT DISTINCT peer_hash FROM lxmf_messages WHERE peer_hash IS NOT NULL
            )
            """,
        )
        self.provider.execute(
            """
            DELETE FROM lxmf_conversation_folders
            WHERE peer_hash NOT IN (
                SELECT DISTINCT peer_hash FROM lxmf_messages WHERE peer_hash IS NOT NULL
            )
            """,
        )
        self.provider.execute(
            """
            DELETE FROM lxmf_conversation_pins
            WHERE peer_hash NOT IN (
                SELECT DISTINCT peer_hash FROM lxmf_messages WHERE peer_hash IS NOT NULL
            )
            """,
        )

    def delete_lxmf_messages_by_hashes(self, message_hashes):
        if not message_hashes:
            return
        placeholders = ", ".join(["?"] * len(message_hashes))
        peers = self.provider.fetchall(
            f"SELECT DISTINCT peer_hash FROM lxmf_messages WHERE hash IN ({placeholders})",
            tuple(message_hashes),
        )
        self.provider.execute(
            f"DELETE FROM lxmf_messages WHERE hash IN ({placeholders})",
            tuple(message_hashes),
        )
        self.refresh_conversation_summaries_for_peers(
            [row["peer_hash"] for row in peers if row and row.get("peer_hash")],
        )

    def delete_lxmf_message_by_hash(self, message_hash):
        row = self.provider.fetchone(
            "SELECT peer_hash FROM lxmf_messages WHERE hash = ?",
            (message_hash,),
        )
        self.provider.execute(
            "DELETE FROM lxmf_messages WHERE hash = ?",
            (message_hash,),
        )
        if row and row.get("peer_hash"):
            self.refresh_conversation_summary(row["peer_hash"])

    def delete_all_lxmf_messages(self):
        with self.provider:
            self.provider.execute("DELETE FROM lxmf_messages")
            self.provider.execute("DELETE FROM lxmf_conversation_read_state")
            self.provider.execute("DELETE FROM lxmf_conversation_summaries")

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

    def get_latest_user_facing_incoming_message(self, peer_hash, *, scan_limit=50):
        """Return the most recent incoming user-facing message for peer_hash.

        Walks recent incoming messages in timestamp-descending order and applies
        is_user_facing_lxmf_payload in Python (the SQLite layer cannot
        cheaply parse the JSON fields blob). scan_limit bounds the walk
        so a long chain of reactions/telemetry won't degrade the bell endpoint.

        Returns None if no user-facing incoming message exists in the
        scanned window.
        """
        from meshchatx.src.backend.lxmf_utils import is_user_facing_lxmf_payload

        rows = self.provider.fetchall(
            "SELECT id, hash, peer_hash, source_hash, destination_hash, "
            "is_incoming, title, "
            "substr(COALESCE(content, ''), 1, 240) as content, "
            "CASE WHEN length(COALESCE(fields, '')) > 16384 THEN NULL ELSE fields END as fields, "
            "CASE WHEN fields IS NOT NULL AND fields != '' AND fields != '{}' "
            "AND (instr(fields, '\"image\"') > 0 OR instr(fields, '\"0x05\"') > 0 "
            "OR instr(fields, '\"audio\"') > 0 OR instr(fields, '\"0x06\"') > 0 "
            "OR instr(fields, '\"file_attachments\"') > 0 OR instr(fields, '\"0x07\"') > 0) "
            "THEN 1 ELSE 0 END as has_attachments, "
            "CASE WHEN fields IS NOT NULL AND fields != '' AND fields != '{}' "
            "AND (instr(fields, '\"reaction\"') > 0 OR instr(fields, '\"0x40\"') > 0) "
            "THEN 1 ELSE 0 END as has_reaction, "
            "CASE WHEN fields IS NOT NULL AND fields != '' AND fields != '{}' "
            "AND (instr(fields, '\"image\"') > 0 OR instr(fields, '\"0x05\"') > 0) "
            "THEN 1 ELSE 0 END as has_image, "
            "CASE WHEN fields IS NOT NULL AND fields != '' AND fields != '{}' "
            "AND (instr(fields, '\"audio\"') > 0 OR instr(fields, '\"0x06\"') > 0) "
            "THEN 1 ELSE 0 END as has_audio, "
            "CASE WHEN fields IS NOT NULL AND fields != '' AND fields != '{}' "
            "AND (instr(fields, '\"file_attachments\"') > 0 OR instr(fields, '\"0x07\"') > 0) "
            "THEN 1 ELSE 0 END as has_files, "
            "timestamp "
            "FROM lxmf_messages WHERE peer_hash = ? AND is_incoming = 1 "
            "ORDER BY timestamp DESC LIMIT ?",
            (peer_hash, scan_limit),
        )
        for row in rows:
            row_dict = dict(row) if not isinstance(row, dict) else row
            fields = row_dict.get("fields")
            if fields is None and (
                row_dict.get("has_attachments")
                or row_dict.get("has_image")
                or row_dict.get("has_audio")
                or row_dict.get("has_files")
            ):
                # Huge attachment blob omitted from SELECT: still user-facing.
                return row_dict
            if row_dict.get("has_reaction") and not (
                (row_dict.get("content") and str(row_dict.get("content")).strip())
                or (row_dict.get("title") and str(row_dict.get("title")).strip())
                or row_dict.get("has_attachments")
            ):
                continue
            if is_user_facing_lxmf_payload(
                fields,
                row_dict.get("content"),
                row_dict.get("title"),
            ):
                return row_dict
        return None

    CONVERSATION_LIST_COLUMNS = (
        "m1.id, m1.hash, m1.source_hash, m1.destination_hash, m1.peer_hash, "
        "m1.state, m1.is_incoming, m1.title, m1.timestamp, m1.created_at, m1.updated_at"
    )

    def get_conversations(self):
        query = f"""
            SELECT {self.CONVERSATION_LIST_COLUMNS}
            FROM lxmf_conversation_summaries s
            INNER JOIN lxmf_messages m1 ON m1.id = s.latest_message_id
            ORDER BY s.latest_message_id DESC
        """
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

    def mark_all_conversations_as_read(self):
        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            """
            INSERT INTO lxmf_conversation_read_state (destination_hash, last_read_at, created_at, updated_at)
            SELECT peer_hash, ?, ?, ? FROM lxmf_messages
            WHERE peer_hash IS NOT NULL
            GROUP BY peer_hash
            ON CONFLICT(destination_hash) DO UPDATE SET
                last_read_at = EXCLUDED.last_read_at,
                updated_at = EXCLUDED.updated_at
            """,
            (now, now, now),
        )

    def get_all_conversation_read_state(self):
        return self.provider.fetchall(
            "SELECT destination_hash, last_read_at, created_at, updated_at "
            "FROM lxmf_conversation_read_state",
        )

    def import_conversation_read_state(self, rows):
        if not isinstance(rows, list) or not rows:
            return 0
        imported = 0
        now = datetime.now(UTC).isoformat()
        with self.provider:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                dest = row.get("destination_hash")
                last_read_at = row.get("last_read_at")
                if not dest or not last_read_at:
                    continue
                self.provider.execute(
                    """
                    INSERT INTO lxmf_conversation_read_state
                        (destination_hash, last_read_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(destination_hash) DO UPDATE SET
                        last_read_at = EXCLUDED.last_read_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (dest, last_read_at, now, now),
                )
                imported += 1
        return imported

    def get_all_notification_viewed_state(self):
        return self.provider.fetchall(
            "SELECT destination_hash, last_viewed_at, created_at, updated_at "
            "FROM notification_viewed_state",
        )

    def import_notification_viewed_state(self, rows):
        if not isinstance(rows, list) or not rows:
            return 0
        imported = 0
        now = datetime.now(UTC).isoformat()
        with self.provider:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                dest = row.get("destination_hash")
                last_viewed_at = row.get("last_viewed_at")
                if not dest or not last_viewed_at:
                    continue
                self.provider.execute(
                    """
                    INSERT INTO notification_viewed_state
                        (destination_hash, last_viewed_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(destination_hash) DO UPDATE SET
                        last_viewed_at = EXCLUDED.last_viewed_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (dest, last_viewed_at, now, now),
                )
                imported += 1
        return imported

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
            SET state = 'generating'
            WHERE is_incoming = 1 AND state = 'failed'
            """,
        )

        # Only outbound messages can get stuck mid-send, as incoming messages are
        # never failed (we already received them).
        self.provider.execute(
            """
            UPDATE lxmf_messages
            SET state = 'failed', updated_at = ?
            WHERE is_incoming = 0
            AND (
                state = 'outbound'
                OR (state = 'sent' AND method = 'opportunistic')
                OR state = 'sending'
                OR state = 'generating'
            )
            """,
            (datetime.now(UTC).isoformat(),),
        )

    def list_duplicate_lxmf_message_hashes_by_content(self) -> list[str]:
        """Hashes of duplicate rows (same peer, direction, and text), excluding the oldest keep.

        Empty or whitespace-only content is ignored so attachment-only or blank
        rows are not collapsed together. Oldest is by timestamp then id.
        """
        groups = self.provider.fetchall(
            """
            SELECT peer_hash, is_incoming, content
            FROM lxmf_messages
            WHERE content IS NOT NULL AND TRIM(content) != ''
            GROUP BY peer_hash, is_incoming, content
            HAVING COUNT(*) > 1
            """,
        )
        to_delete: list[str] = []
        for group in groups:
            rows = self.provider.fetchall(
                """
                SELECT hash
                FROM lxmf_messages
                WHERE peer_hash = ?
                  AND is_incoming = ?
                  AND content = ?
                ORDER BY
                    CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
                    timestamp ASC,
                    id ASC
                """,
                (group["peer_hash"], group["is_incoming"], group["content"]),
            )
            # Keep the first (oldest); delete the rest.
            for row in rows[1:]:
                if row.get("hash"):
                    to_delete.append(row["hash"])
        return to_delete

    def count_duplicate_lxmf_messages_by_content(self) -> int:
        return len(self.list_duplicate_lxmf_message_hashes_by_content())

    def delete_duplicate_lxmf_messages_by_content(self) -> int:
        """Delete content-duplicate message rows, keeping the oldest per group."""
        hashes = self.list_duplicate_lxmf_message_hashes_by_content()
        if not hashes:
            return 0
        self.delete_lxmf_messages_by_hashes(hashes)
        self.prune_conversation_metadata_for_peers_with_no_messages()
        return len(hashes)

    def get_failed_messages_for_destination(self, destination_hash):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_messages WHERE state = 'failed' AND peer_hash = ? ORDER BY id ASC",
            (destination_hash,),
        )

    def try_claim_failed_message_for_auto_resend(
        self,
        message_hash: str,
        *,
        cooldown_until: float,
        now: float,
    ) -> bool:
        """Atomically claim a failed row for one auto-resend attempt.

        Sets next_delivery_attempt_at into the future so overlapping announce,
        ping, and path handlers cannot claim the same row again until cooldown.
        """
        now_iso = datetime.now(UTC).isoformat()
        cursor = self.provider.execute(
            """
            UPDATE lxmf_messages
            SET next_delivery_attempt_at = ?, updated_at = ?
            WHERE hash = ?
              AND state = 'failed'
              AND (
                next_delivery_attempt_at IS NULL
                OR next_delivery_attempt_at <= ?
              )
            """,
            (float(cooldown_until), now_iso, message_hash, float(now)),
        )
        return bool(cursor and cursor.rowcount and cursor.rowcount > 0)

    def set_message_fields_json(self, message_hash: str, fields_json: str) -> None:
        now_iso = datetime.now(UTC).isoformat()
        self.provider.execute(
            "UPDATE lxmf_messages SET fields = ?, updated_at = ? WHERE hash = ?",
            (fields_json, now_iso, message_hash),
        )

    def set_auto_resend_count_on_message(self, message_hash: str, count: int) -> None:
        from meshchatx.src.backend.auto_resend_guard import (
            fields_with_auto_resend_count,
        )

        row = self.provider.fetchone(
            "SELECT fields FROM lxmf_messages WHERE hash = ?",
            (message_hash,),
        )
        if not row:
            return
        self.set_message_fields_json(
            message_hash,
            fields_with_auto_resend_count(row.get("fields"), count),
        )

    def has_recent_outbound_with_content(
        self,
        peer_hash: str,
        content: str | None,
        *,
        within_seconds: float,
        now: float | None = None,
    ) -> bool:
        """True when a recent non-failed outbound already carries the same body."""
        import time as _time

        now_ts = float(now if now is not None else _time.time())
        cutoff = now_ts - float(within_seconds)
        row = self.provider.fetchone(
            """
            SELECT 1 AS ok FROM lxmf_messages
            WHERE peer_hash = ?
              AND is_incoming = 0
              AND state != 'failed'
              AND content = ?
              AND timestamp IS NOT NULL
              AND timestamp >= ?
            LIMIT 1
            """,
            (peer_hash, content if content is not None else "", cutoff),
        )
        return bool(row)

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
        """
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
            f"SELECT peer_hash, COUNT(*) as count FROM lxmf_messages WHERE state = 'failed' AND peer_hash IN ({placeholders}) GROUP BY peer_hash",
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
        """
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
        query = f"INSERT INTO lxmf_forwarding_mappings ({columns}, created_at) VALUES ({placeholders}, ?)"
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
                    f"DELETE FROM lxmf_conversation_folders WHERE peer_hash IN ({placeholders})",
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
