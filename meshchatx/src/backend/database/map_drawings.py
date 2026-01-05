from datetime import UTC, datetime

from .provider import DatabaseProvider


class MapDrawingsDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def upsert_drawing(self, identity_hash, name, data):
        now = datetime.now(UTC)
        # Check if drawing with same name exists for this user
        existing = self.provider.fetchone(
            "SELECT id FROM map_drawings WHERE identity_hash = ? AND name = ?",
            (identity_hash, name),
        )

        if existing:
            self.provider.execute(
                "UPDATE map_drawings SET data = ?, updated_at = ? WHERE id = ?",
                (data, now, existing["id"]),
            )
        else:
            self.provider.execute(
                """
                INSERT INTO map_drawings (identity_hash, name, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (identity_hash, name, data, now, now),
            )

    def get_drawings(self, identity_hash):
        return self.provider.fetchall(
            "SELECT * FROM map_drawings WHERE identity_hash = ? ORDER BY updated_at DESC",
            (identity_hash,),
        )

    def delete_drawing(self, drawing_id):
        self.provider.execute(
            "DELETE FROM map_drawings WHERE id = ?",
            (drawing_id,),
        )

    def update_drawing(self, drawing_id, name, data):
        now = datetime.now(UTC)
        self.provider.execute(
            "UPDATE map_drawings SET name = ?, data = ?, updated_at = ? WHERE id = ?",
            (name, data, now, drawing_id),
        )
