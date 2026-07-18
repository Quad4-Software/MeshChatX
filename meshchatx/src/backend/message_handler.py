# SPDX-License-Identifier: 0BSD

from .database import Database


def _strip_utf16_surrogates(text):
    if text is None:
        return None
    return "".join(c for c in str(text) if not (0xD800 <= ord(c) <= 0xDFFF))


class MessageHandler:
    def __init__(self, db: Database):
        self.db = db

    # Columns needed by convert_db_lxmf_message_to_dict / ConversationViewer.
    # Prefer fields_meta (no attachment bytes). Fall back to small fields only.
    _CONVERSATION_MESSAGE_COLUMNS = """
            id, hash, source_hash, destination_hash, peer_hash, state, progress,
            is_incoming, method, delivery_attempts, next_delivery_attempt_at,
            title, content, timestamp, rssi, snr, quality, is_spam, reply_to_hash,
            attachments_stripped, path_hops_at_send, path_interface_at_send,
            path_finding_measure, path_row_hash_hex, created_at, updated_at,
            COALESCE(has_image, 0) as has_image,
            COALESCE(has_audio, 0) as has_audio,
            COALESCE(has_files, 0) as has_files,
            COALESCE(has_reaction, 0) as has_reaction,
            COALESCE(has_telemetry, 0) as has_telemetry,
            CASE
                WHEN fields_meta IS NOT NULL AND fields_meta != '' THEN fields_meta
                WHEN length(COALESCE(fields, '')) <= 16384 THEN fields
                ELSE NULL
            END as fields
    """

    # Default and hard cap when callers omit or overshoot limit.
    DEFAULT_CONVERSATIONS_LIMIT = 500
    MAX_CONVERSATIONS_LIMIT = 2000

    def get_conversation_messages(
        self,
        local_hash,
        destination_hash,
        limit=100,
        offset=0,
        after_id=None,
        before_id=None,
    ):
        query = f"""
            SELECT {self._CONVERSATION_MESSAGE_COLUMNS}
            FROM lxmf_messages
            WHERE peer_hash = ?
        """
        params = [destination_hash]

        if after_id:
            query += " AND id > ?"
            params.append(after_id)
        if before_id:
            query += " AND id < ?"
            params.append(before_id)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return self.db.provider.fetchall(query, params)

    def delete_conversation(self, local_hash, destination_hash):
        query = "DELETE FROM lxmf_messages WHERE peer_hash = ?"
        self.db.provider.execute(query, [destination_hash])
        self.db.provider.execute(
            "DELETE FROM lxmf_conversation_read_state WHERE destination_hash = ?",
            [destination_hash],
        )
        # Also clean up folder mapping
        self.db.provider.execute(
            "DELETE FROM lxmf_conversation_folders WHERE peer_hash = ?",
            [destination_hash],
        )
        self.db.provider.execute(
            "DELETE FROM lxmf_conversation_pins WHERE peer_hash = ?",
            [destination_hash],
        )
        self.db.messages.delete_conversation_summary(destination_hash)

    def search_messages(self, local_hash, search_term, limit=500):
        search_term = _strip_utf16_surrogates(search_term) or ""
        like_term = f"%{search_term}%"
        query = """
            SELECT peer_hash, MAX(timestamp) as max_ts
            FROM lxmf_messages
            WHERE title LIKE ? OR content LIKE ? OR peer_hash LIKE ?
            GROUP BY peer_hash
            ORDER BY max_ts DESC
            LIMIT ?
        """
        params = [like_term, like_term, like_term, limit]
        return self.db.provider.fetchall(query, params)

    # Keep conversation-list payloads small. Full fields often embeds
    # multi-MB base64 attachments and must never be loaded into the list API.
    # Prefer persisted has_* columns (schema v51+). Fall back to instr only
    # when flags were never backfilled (NULL) on filter paths.
    _CONVERSATION_CONTENT_PREVIEW_CHARS = 240
    _FIELDS_HAS_IMAGE_SQL = "COALESCE(s.has_image, 0)"
    _FIELDS_HAS_AUDIO_SQL = "COALESCE(s.has_audio, 0)"
    _FIELDS_HAS_FILES_SQL = "COALESCE(s.has_files, 0)"
    _FIELDS_HAS_REACTION_SQL = "COALESCE(s.has_reaction, 0)"
    _FIELDS_HAS_TELEMETRY_SQL = "COALESCE(s.has_telemetry, 0)"
    _FIELDS_HAS_ATTACHMENTS_SQL = (
        f"({_FIELDS_HAS_IMAGE_SQL} = 1 OR {_FIELDS_HAS_AUDIO_SQL} = 1 "
        f"OR {_FIELDS_HAS_FILES_SQL} = 1)"
    )
    # Filter path: prefer summary has_* so filter_has_attachments stays cheap.
    _FILTER_HAS_ATTACHMENTS_SQL = (
        "(COALESCE(s.has_image, 0) = 1 OR COALESCE(s.has_audio, 0) = 1 "
        "OR COALESCE(s.has_files, 0) = 1)"
    )

    @classmethod
    def clamp_conversations_limit(cls, limit):
        """Normalize list limit. None becomes the default. Cap at MAX."""
        if limit is None:
            return cls.DEFAULT_CONVERSATIONS_LIMIT
        try:
            value = int(limit)
        except (TypeError, ValueError):
            return cls.DEFAULT_CONVERSATIONS_LIMIT
        if value < 0:
            return 0
        if value > cls.MAX_CONVERSATIONS_LIMIT:
            return cls.MAX_CONVERSATIONS_LIMIT
        return value

    def get_conversations(
        self,
        local_hash,
        search=None,
        filter_unread=False,
        filter_failed=False,
        filter_has_attachments=False,
        folder_id=None,
        limit=500,
        offset=0,
    ):
        limit = self.clamp_conversations_limit(limit)
        try:
            offset = max(0, int(offset or 0))
        except (TypeError, ValueError):
            offset = 0

        query = f"""
            SELECT
                s.latest_message_id as id,
                s.latest_message_hash as hash,
                s.source_hash, s.destination_hash,
                s.peer_hash, s.state, s.progress, s.is_incoming,
                s.title,
                s.content_preview as content,
                s.timestamp,
                s.is_spam, s.reply_to_hash,
                s.created_at, s.updated_at,
                ({self._FIELDS_HAS_IMAGE_SQL}) as has_image,
                ({self._FIELDS_HAS_AUDIO_SQL}) as has_audio,
                ({self._FIELDS_HAS_FILES_SQL}) as has_files,
                ({self._FIELDS_HAS_REACTION_SQL}) as has_reaction,
                ({self._FIELDS_HAS_TELEMETRY_SQL}) as has_telemetry,
                CASE WHEN {self._FIELDS_HAS_ATTACHMENTS_SQL} THEN 1 ELSE 0 END as has_attachments,
                a.app_data as peer_app_data,
                c.display_name as custom_display_name,
                CASE
                    WHEN con.custom_image IS NOT NULL AND con.custom_image != ''
                    THEN 1 ELSE 0
                END as has_contact_image,
                con.name as contact_name,
                i.icon_name, i.foreground_colour, i.background_colour,
                r.last_read_at,
                f.id as folder_id,
                fn.name as folder_name,
                COALESCE(s.failed_count, 0) as failed_count,
                CASE WHEN con.id IS NOT NULL THEN 1 ELSE 0 END as is_contact
            FROM lxmf_conversation_summaries s
            LEFT JOIN announces a ON a.destination_hash = s.peer_hash
            LEFT JOIN custom_destination_display_names c ON c.destination_hash = s.peer_hash
            LEFT JOIN contacts con ON (
                con.remote_identity_hash = s.peer_hash OR
                con.lxmf_address = s.peer_hash OR
                con.lxst_address = s.peer_hash
            )
            LEFT JOIN lxmf_user_icons i ON i.destination_hash = s.peer_hash
            LEFT JOIN lxmf_conversation_read_state r ON r.destination_hash = s.peer_hash
            LEFT JOIN lxmf_conversation_folders f ON f.peer_hash = s.peer_hash
            LEFT JOIN lxmf_folders fn ON fn.id = f.folder_id
        """
        params = []
        where_clauses = []

        if folder_id is not None:
            if folder_id in {0, "0"}:
                # Special case: no folder (Uncategorized)
                where_clauses.append("f.folder_id IS NULL")
            else:
                where_clauses.append("f.folder_id = ?")
                params.append(folder_id)

        if filter_unread:
            where_clauses.append(
                "(s.is_incoming = 1 AND (r.last_read_at IS NULL OR s.timestamp > strftime('%s', r.last_read_at)))",
            )

        if filter_failed:
            where_clauses.append("s.state = 'failed'")

        if filter_has_attachments:
            where_clauses.append(self._FILTER_HAS_ATTACHMENTS_SQL)

        if search:
            search = _strip_utf16_surrogates(search) or ""
            if search:
                like_term = f"%{search}%"
                # Search latest summary fields or any historical message for the peer
                where_clauses.append("""
                    (s.title LIKE ? OR s.content_preview LIKE ? OR s.peer_hash LIKE ?
                     OR c.display_name LIKE ? OR con.name LIKE ?
                     OR s.peer_hash IN (
                        SELECT peer_hash FROM lxmf_messages
                        WHERE title LIKE ? OR content LIKE ?
                     ))
                """)
                params.extend(
                    [
                        like_term,
                        like_term,
                        like_term,
                        like_term,
                        like_term,
                        like_term,
                        like_term,
                    ],
                )

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " GROUP BY s.peer_hash ORDER BY s.latest_message_id DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return self.db.provider.fetchall(query, params)
