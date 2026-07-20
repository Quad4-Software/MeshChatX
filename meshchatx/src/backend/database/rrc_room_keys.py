# SPDX-License-Identifier: 0BSD

"""DAO for encrypted RRC client room keys."""

from __future__ import annotations

from .provider import DatabaseProvider


class RrcRoomKeysDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def upsert(
        self,
        hub_hash: str,
        dest_name: str,
        room: str,
        nonce: bytes,
        ciphertext: bytes,
    ) -> None:
        self.provider.execute(
            """
            INSERT INTO rrc_room_keys (
                hub_hash, dest_name, room, nonce, ciphertext, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(hub_hash, dest_name, room) DO UPDATE SET
                nonce = EXCLUDED.nonce,
                ciphertext = EXCLUDED.ciphertext,
                updated_at = CURRENT_TIMESTAMP
            """,
            (hub_hash, dest_name, room, bytes(nonce), bytes(ciphertext)),
        )

    def get(self, hub_hash: str, dest_name: str, room: str):
        return self.provider.fetchone(
            """
            SELECT hub_hash, dest_name, room, nonce, ciphertext, updated_at
            FROM rrc_room_keys
            WHERE hub_hash = ? AND dest_name = ? AND room = ?
            """,
            (hub_hash, dest_name, room),
        )

    def list_for_hub(self, hub_hash: str, dest_name: str | None = None):
        if dest_name is None:
            return self.provider.fetchall(
                """
                SELECT hub_hash, dest_name, room, updated_at
                FROM rrc_room_keys
                WHERE hub_hash = ?
                ORDER BY room ASC
                """,
                (hub_hash,),
            )
        return self.provider.fetchall(
            """
            SELECT hub_hash, dest_name, room, updated_at
            FROM rrc_room_keys
            WHERE hub_hash = ? AND dest_name = ?
            ORDER BY room ASC
            """,
            (hub_hash, dest_name),
        )

    def delete(self, hub_hash: str, dest_name: str, room: str) -> int:
        cursor = self.provider.execute(
            """
            DELETE FROM rrc_room_keys
            WHERE hub_hash = ? AND dest_name = ? AND room = ?
            """,
            (hub_hash, dest_name, room),
        )
        return int(getattr(cursor, "rowcount", 0) or 0)

    def delete_for_hub(self, hub_hash: str, dest_name: str | None = None) -> int:
        if dest_name is None:
            cursor = self.provider.execute(
                "DELETE FROM rrc_room_keys WHERE hub_hash = ?",
                (hub_hash,),
            )
        else:
            cursor = self.provider.execute(
                "DELETE FROM rrc_room_keys WHERE hub_hash = ? AND dest_name = ?",
                (hub_hash, dest_name),
            )
        return int(getattr(cursor, "rowcount", 0) or 0)
