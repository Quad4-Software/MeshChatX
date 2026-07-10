# SPDX-License-Identifier: 0BSD

from datetime import UTC, datetime

from .provider import DatabaseProvider


class MapOverlaysDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def count_for_identity(self, identity_hash: str) -> int:
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM map_overlay_sources WHERE identity_hash = ?",
            (identity_hash,),
        )
        return int(row["c"]) if row else 0

    def get_by_id(self, overlay_id: int):
        return self.provider.fetchone(
            "SELECT * FROM map_overlay_sources WHERE id = ?",
            (overlay_id,),
        )

    def get_by_unique(
        self,
        identity_hash: str,
        kind: str,
        destination_hash: str,
        path_or_repo_path: str,
        ref: str,
    ):
        return self.provider.fetchone(
            """
            SELECT * FROM map_overlay_sources
            WHERE identity_hash = ?
              AND kind = ?
              AND destination_hash = ?
              AND path_or_repo_path = ?
              AND ref = ?
            """,
            (identity_hash, kind, destination_hash, path_or_repo_path, ref),
        )

    def list_for_identity(self, identity_hash: str):
        return self.provider.fetchall(
            """
            SELECT * FROM map_overlay_sources
            WHERE identity_hash = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (identity_hash,),
        )

    def list_due_autorefresh(self, now_iso: str):
        return self.provider.fetchall(
            """
            SELECT * FROM map_overlay_sources
            WHERE enabled = 1
              AND refresh_interval_seconds > 0
              AND status != 'fetching'
              AND (
                    next_refresh_at IS NULL
                    OR next_refresh_at <= ?
                  )
            ORDER BY (next_refresh_at IS NOT NULL), next_refresh_at ASC, id ASC
            """,
            (now_iso,),
        )

    def insert(
        self,
        identity_hash: str,
        *,
        kind: str,
        destination_hash: str,
        path_or_repo_path: str,
        ref: str,
        name: str,
        group_name: str | None = None,
        repository: str | None = None,
        enabled: int = 1,
        visible: int = 1,
        refresh_interval_seconds: int = 0,
        status: str = "pending",
    ) -> int:
        now = datetime.now(UTC)
        cur = self.provider.execute(
            """
            INSERT INTO map_overlay_sources (
                identity_hash, kind, destination_hash, path_or_repo_path, ref,
                group_name, repository, name, enabled, visible,
                refresh_interval_seconds, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identity_hash,
                kind,
                destination_hash,
                path_or_repo_path,
                ref,
                group_name,
                repository,
                name,
                enabled,
                visible,
                refresh_interval_seconds,
                status,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)

    def update_fields(self, overlay_id: int, **fields) -> None:
        if not fields:
            return
        fields = dict(fields)
        fields["updated_at"] = datetime.now(UTC)
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [overlay_id]
        self.provider.execute(
            f"UPDATE map_overlay_sources SET {cols} WHERE id = ?",
            tuple(values),
        )

    def delete(self, overlay_id: int) -> None:
        self.provider.execute(
            "DELETE FROM map_overlay_sources WHERE id = ?",
            (overlay_id,),
        )

    def delete_for_identity(self, identity_hash: str, overlay_id: int) -> bool:
        row = self.get_by_id(overlay_id)
        if not row or row["identity_hash"] != identity_hash:
            return False
        self.delete(overlay_id)
        return True
