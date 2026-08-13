# SPDX-License-Identifier: 0BSD

from datetime import UTC, datetime

from .provider import DatabaseProvider


class MapPublishedDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def list_for_identity(self, identity_hash: str):
        return self.provider.fetchall(
            """
            SELECT * FROM map_published
            WHERE identity_hash = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (identity_hash,),
        )

    def get_by_map_id(self, identity_hash: str, map_id: str):
        return self.provider.fetchone(
            """
            SELECT * FROM map_published
            WHERE identity_hash = ? AND map_id = ?
            """,
            (identity_hash, map_id),
        )

    def insert(
        self,
        identity_hash: str,
        *,
        map_id: str,
        name: str,
        format: str,
        size: int,
        sha256: str,
        bbox: str | None,
        feature_count: int,
        path: str,
    ) -> int:
        now = datetime.now(UTC).isoformat()
        cur = self.provider.execute(
            """
            INSERT INTO map_published (
                identity_hash, map_id, name, format, size, sha256,
                bbox, feature_count, path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identity_hash,
                map_id,
                name,
                format,
                size,
                sha256,
                bbox,
                feature_count,
                path,
                now,
                now,
            ),
        )
        return int(cur.lastrowid or 0)

    def delete(self, identity_hash: str, map_id: str) -> bool:
        cur = self.provider.execute(
            "DELETE FROM map_published WHERE identity_hash = ? AND map_id = ?",
            (identity_hash, map_id),
        )
        return int(cur.rowcount or 0) > 0

    def count_for_identity(self, identity_hash: str) -> int:
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM map_published WHERE identity_hash = ?",
            (identity_hash,),
        )
        return int(row["c"]) if row else 0
