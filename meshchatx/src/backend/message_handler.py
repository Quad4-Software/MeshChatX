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
            WHERE ((source_hash = ? AND destination_hash = ?) 
               OR (destination_hash = ? AND source_hash = ?))
        """
        params = [local_hash, destination_hash, local_hash, destination_hash]

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
        query = """
            DELETE FROM lxmf_messages 
            WHERE ((source_hash = ? AND destination_hash = ?) 
               OR (destination_hash = ? AND source_hash = ?))
        """
        self.db.provider.execute(
            query,
            [local_hash, destination_hash, local_hash, destination_hash],
        )

    def search_messages(self, local_hash, search_term):
        like_term = f"%{search_term}%"
        query = """
            SELECT source_hash, destination_hash, MAX(timestamp) as max_ts
            FROM lxmf_messages
            WHERE (source_hash = ? OR destination_hash = ?)
              AND (title LIKE ? OR content LIKE ? OR source_hash LIKE ? OR destination_hash LIKE ?)
            GROUP BY source_hash, destination_hash
        """
        params = [local_hash, local_hash, like_term, like_term, like_term, like_term]
        return self.db.provider.fetchall(query, params)

    def get_conversations(self, local_hash, filter_unread=False):
        # Implementation moved from get_conversations DAO but with local_hash filter
        query = """
            SELECT m1.* FROM lxmf_messages m1
            JOIN (
                SELECT 
                    CASE WHEN source_hash = ? THEN destination_hash ELSE source_hash END as peer_hash,
                    MAX(timestamp) as max_ts
                FROM lxmf_messages
                WHERE source_hash = ? OR destination_hash = ?
                GROUP BY peer_hash
            ) m2 ON (CASE WHEN m1.source_hash = ? THEN m1.destination_hash ELSE m1.source_hash END = m2.peer_hash 
                     AND m1.timestamp = m2.max_ts)
            WHERE (m1.source_hash = ? OR m1.destination_hash = ?)
        """
        params = [
            local_hash,
            local_hash,
            local_hash,
            local_hash,
            local_hash,
            local_hash,
        ]

        if filter_unread:
            query += " AND EXISTS (SELECT 1 FROM lxmf_messages m3 WHERE (m3.source_hash = m2.peer_hash AND m3.destination_hash = ?) AND m3.state = 'received' AND m3.is_incoming = 1)"
            params.append(local_hash)

        query += " ORDER BY m1.timestamp DESC"

        return self.db.provider.fetchall(query, params)
