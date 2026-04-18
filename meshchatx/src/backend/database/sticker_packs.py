# SPDX-License-Identifier: 0BSD

"""Data access object for sticker packs.

Packs group multiple stickers under a single user-facing label so they can be
exported, shared with peers over LXMF, or installed from a peer's pack
attachment. Stickers belonging to a pack reference it via
``user_stickers.pack_id``.
"""

from __future__ import annotations

import sqlite3
import time

from meshchatx.src.backend import sticker_pack_utils, sticker_utils


_PACK_COLUMNS = (
    "id, identity_hash, title, short_name, description, pack_type, author, "
    "is_strict, cover_sticker_id, sort_order, created_at, updated_at"
)


class UserStickerPacksDAO:
    """CRUD for ``user_sticker_packs``."""

    def __init__(self, provider):
        self.provider = provider

    def count_for_identity(self, identity_hash: str) -> int:
        """Return the number of packs stored for ``identity_hash``."""
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM user_sticker_packs WHERE identity_hash = ?",
            (identity_hash,),
        )
        return int(row["c"]) if row else 0

    def list_for_identity(self, identity_hash: str):
        """List packs for ``identity_hash`` ordered by user-defined sort order."""
        return self.provider.fetchall(
            f"""
            SELECT {_PACK_COLUMNS}
            FROM user_sticker_packs
            WHERE identity_hash = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (identity_hash,),
        )

    def get_row(self, pack_id: int, identity_hash: str):
        """Fetch a single pack row scoped to ``identity_hash``."""
        return self.provider.fetchone(
            f"""
            SELECT {_PACK_COLUMNS}
            FROM user_sticker_packs
            WHERE id = ? AND identity_hash = ?
            """,
            (pack_id, identity_hash),
        )

    def get_by_short_name(self, identity_hash: str, short_name: str):
        """Fetch a pack by its identity-scoped ``short_name`` slug."""
        return self.provider.fetchone(
            f"""
            SELECT {_PACK_COLUMNS}
            FROM user_sticker_packs
            WHERE identity_hash = ? AND short_name = ?
            """,
            (identity_hash, short_name),
        )

    def insert(
        self,
        identity_hash: str,
        title: str | None,
        *,
        short_name: str | None = None,
        description: str | None = None,
        pack_type: str | None = None,
        author: str | None = None,
        is_strict: bool = True,
    ) -> dict:
        """Create a new pack. Raises ``ValueError`` on quota or short_name clash."""
        if (
            self.count_for_identity(identity_hash)
            >= sticker_utils.MAX_STICKER_PACKS_PER_IDENTITY
        ):
            msg = "pack_limit_reached"
            raise ValueError(msg)
        sn = sticker_pack_utils.sanitize_pack_short_name(short_name)
        if sn is not None and self.get_by_short_name(identity_hash, sn) is not None:
            msg = "duplicate_pack_short_name"
            raise ValueError(msg)
        now = time.time()
        try:
            cur = self.provider.execute(
                """
                INSERT INTO user_sticker_packs (
                    identity_hash, title, short_name, description, pack_type,
                    author, is_strict, cover_sticker_id, sort_order,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    identity_hash,
                    sticker_pack_utils.sanitize_pack_title(title),
                    sn,
                    sticker_pack_utils.sanitize_pack_description(description),
                    sticker_pack_utils.sanitize_pack_type(pack_type),
                    (author or "")[:80] or None,
                    1 if is_strict else 0,
                    self.count_for_identity(identity_hash),
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            msg = "duplicate_pack_short_name"
            raise ValueError(msg) from exc
        return dict(self.get_row(cur.lastrowid, identity_hash))

    def update(
        self,
        pack_id: int,
        identity_hash: str,
        *,
        title: str | None = None,
        description: str | None = None,
        pack_type: str | None = None,
        cover_sticker_id: int | None | object = ...,
    ) -> bool:
        """Update mutable fields of an existing pack.

        ``cover_sticker_id`` uses a sentinel default so callers can clear the
        cover by passing ``None`` while leaving it untouched when omitted.
        """
        existing = self.get_row(pack_id, identity_hash)
        if not existing:
            return False
        new_title = (
            sticker_pack_utils.sanitize_pack_title(title)
            if title is not None
            else existing["title"]
        )
        new_desc = (
            sticker_pack_utils.sanitize_pack_description(description)
            if description is not None
            else existing["description"]
        )
        new_type = (
            sticker_pack_utils.sanitize_pack_type(pack_type)
            if pack_type is not None
            else existing["pack_type"]
        )
        new_cover = (
            existing["cover_sticker_id"]
            if cover_sticker_id is ...
            else cover_sticker_id
        )
        cur = self.provider.execute(
            """
            UPDATE user_sticker_packs
            SET title = ?, description = ?, pack_type = ?, cover_sticker_id = ?,
                updated_at = ?
            WHERE id = ? AND identity_hash = ?
            """,
            (
                new_title,
                new_desc,
                new_type,
                new_cover,
                time.time(),
                pack_id,
                identity_hash,
            ),
        )
        return cur.rowcount > 0

    def reorder(
        self,
        identity_hash: str,
        ordered_pack_ids: list[int],
    ) -> int:
        """Persist a new sort order for the listed packs."""
        now = time.time()
        updated = 0
        for index, pid in enumerate(ordered_pack_ids):
            cur = self.provider.execute(
                """
                UPDATE user_sticker_packs
                SET sort_order = ?, updated_at = ?
                WHERE id = ? AND identity_hash = ?
                """,
                (index, now, int(pid), identity_hash),
            )
            updated += cur.rowcount
        return updated

    def delete(self, pack_id: int, identity_hash: str) -> bool:
        """Delete a pack and detach its stickers (set ``pack_id`` to NULL)."""
        self.provider.execute(
            """
            UPDATE user_stickers SET pack_id = NULL
            WHERE pack_id = ? AND identity_hash = ?
            """,
            (pack_id, identity_hash),
        )
        cur = self.provider.execute(
            "DELETE FROM user_sticker_packs WHERE id = ? AND identity_hash = ?",
            (pack_id, identity_hash),
        )
        return cur.rowcount > 0

    def delete_with_stickers(self, pack_id: int, identity_hash: str) -> bool:
        """Delete a pack and all of its stickers."""
        self.provider.execute(
            "DELETE FROM user_stickers WHERE pack_id = ? AND identity_hash = ?",
            (pack_id, identity_hash),
        )
        cur = self.provider.execute(
            "DELETE FROM user_sticker_packs WHERE id = ? AND identity_hash = ?",
            (pack_id, identity_hash),
        )
        return cur.rowcount > 0
