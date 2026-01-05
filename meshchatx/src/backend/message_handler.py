from .database import Database


class MessageHandler:
    def __init__(self, db: Database):
        self.db = db

    def get_conversation_messages(
        self,
        local_hash,
        destination_hash,
        limit=100,
        offset=0,
        after_id=None,
        before_id=None,
    ):
        query = """
            SELECT * FROM lxmf_messages 
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
        # Also clean up folder mapping
        self.db.provider.execute(
            "DELETE FROM lxmf_conversation_folders WHERE peer_hash = ?",
            [destination_hash],
        )

    def search_messages(self, local_hash, search_term):
        like_term = f"%{search_term}%"
        query = """
            SELECT peer_hash, MAX(timestamp) as max_ts
            FROM lxmf_messages
            WHERE title LIKE ? OR content LIKE ? OR peer_hash LIKE ?
            GROUP BY peer_hash
        """
        params = [like_term, like_term, like_term]
        return self.db.provider.fetchall(query, params)

    def get_conversations(
        self,
        local_hash,
        search=None,
        filter_unread=False,
        filter_failed=False,
        filter_has_attachments=False,
        folder_id=None,
        limit=None,
        offset=0,
    ):
        # Optimized using peer_hash column and JOINs to avoid N+1 queries
        query = """
            SELECT 
                m1.*, 
                a.app_data as peer_app_data, 
                c.display_name as custom_display_name,
                con.custom_image as contact_image,
                i.icon_name, i.foreground_colour, i.background_colour,
                r.last_read_at,
                f.id as folder_id,
                fn.name as folder_name,
                (SELECT COUNT(*) FROM lxmf_messages m_failed 
                 WHERE m_failed.peer_hash = m1.peer_hash AND m_failed.state = 'failed') as failed_count
            FROM lxmf_messages m1
            INNER JOIN (
                SELECT peer_hash, MAX(timestamp) as max_ts
                FROM lxmf_messages
                WHERE peer_hash IS NOT NULL
                GROUP BY peer_hash
            ) m2 ON m1.peer_hash = m2.peer_hash AND m1.timestamp = m2.max_ts
            LEFT JOIN announces a ON a.destination_hash = m1.peer_hash
            LEFT JOIN custom_destination_display_names c ON c.destination_hash = m1.peer_hash
            LEFT JOIN contacts con ON (
                con.remote_identity_hash = m1.peer_hash OR 
                con.lxmf_address = m1.peer_hash OR 
                con.lxst_address = m1.peer_hash
            )
            LEFT JOIN lxmf_user_icons i ON i.destination_hash = m1.peer_hash
            LEFT JOIN lxmf_conversation_read_state r ON r.destination_hash = m1.peer_hash
            LEFT JOIN lxmf_conversation_folders f ON f.peer_hash = m1.peer_hash
            LEFT JOIN lxmf_folders fn ON fn.id = f.folder_id
        """
        params = []
        where_clauses = []

        if folder_id is not None:
            if folder_id == 0 or folder_id == "0":
                # Special case: no folder (Uncategorized)
                where_clauses.append("f.folder_id IS NULL")
            else:
                where_clauses.append("f.folder_id = ?")
                params.append(folder_id)

        if filter_unread:
            where_clauses.append(
                "(r.last_read_at IS NULL OR m1.timestamp > strftime('%s', r.last_read_at))",
            )

        if filter_failed:
            where_clauses.append("m1.state = 'failed'")

        if filter_has_attachments:
            where_clauses.append(
                "(m1.fields IS NOT NULL AND m1.fields != '{}' AND m1.fields != '')",
            )

        if search:
            like_term = f"%{search}%"
            # Search in latest message info OR search across ALL messages for this peer
            where_clauses.append("""
                (m1.title LIKE ? OR m1.content LIKE ? OR m1.peer_hash LIKE ? OR c.display_name LIKE ?
                 OR m1.peer_hash IN (SELECT peer_hash FROM lxmf_messages WHERE title LIKE ? OR content LIKE ?))
            """)
            params.extend(
                [like_term, like_term, like_term, like_term, like_term, like_term],
            )

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " GROUP BY m1.peer_hash ORDER BY m1.timestamp DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        return self.db.provider.fetchall(query, params)
