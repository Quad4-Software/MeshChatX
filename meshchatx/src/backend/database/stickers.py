# SPDX-License-Identifier: 0BSD

import base64
import sqlite3
import time

from meshchatx.src.backend import sticker_utils


_STICKER_SUMMARY_COLUMNS = (
    "id, identity_hash, name, image_type, length(image_blob) AS image_size, "
    "content_hash, source_message_hash, pack_id, emoji, width, height, "
    "duration_ms, fps, is_animated, is_video, is_strict, sort_order, "
    "created_at, updated_at"
)

_STICKER_FULL_COLUMNS = (
    "id, identity_hash, name, image_type, image_blob, content_hash, "
    "source_message_hash, pack_id, emoji, width, height, duration_ms, fps, "
    "is_animated, is_video, is_strict, sort_order, created_at, updated_at"
)


class UserStickersDAO:
    """Data access object for individual stickers stored per identity."""

    def __init__(self, provider):
        self.provider = provider

    def count_for_identity(self, identity_hash: str) -> int:
        """Return the total number of stickers stored for ``identity_hash``."""
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM user_stickers WHERE identity_hash = ?",
            (identity_hash,),
        )
        return int(row["c"]) if row else 0

    def count_for_pack(self, pack_id: int, identity_hash: str) -> int:
        """Return the number of stickers belonging to ``pack_id``."""
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM user_stickers WHERE pack_id = ? AND identity_hash = ?",
            (pack_id, identity_hash),
        )
        return int(row["c"]) if row else 0

    def list_for_identity(self, identity_hash: str):
        """List all sticker summaries for ``identity_hash``, newest first."""
        return self.provider.fetchall(
            f"""
            SELECT {_STICKER_SUMMARY_COLUMNS}
            FROM user_stickers
            WHERE identity_hash = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (identity_hash,),
        )

    def list_for_pack(self, pack_id: int, identity_hash: str):
        """List sticker summaries belonging to a pack, ordered by ``sort_order``."""
        return self.provider.fetchall(
            f"""
            SELECT {_STICKER_SUMMARY_COLUMNS}
            FROM user_stickers
            WHERE pack_id = ? AND identity_hash = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (pack_id, identity_hash),
        )

    def list_unpacked(self, identity_hash: str):
        """List sticker summaries that do not belong to any pack."""
        return self.provider.fetchall(
            f"""
            SELECT {_STICKER_SUMMARY_COLUMNS}
            FROM user_stickers
            WHERE identity_hash = ? AND pack_id IS NULL
            ORDER BY updated_at DESC, id DESC
            """,
            (identity_hash,),
        )

    def get_row(self, sticker_id: int, identity_hash: str):
        """Fetch the full row (including ``image_blob``) for a sticker."""
        return self.provider.fetchone(
            f"""
            SELECT {_STICKER_FULL_COLUMNS}
            FROM user_stickers
            WHERE id = ? AND identity_hash = ?
            """,
            (sticker_id, identity_hash),
        )

    def delete(self, sticker_id: int, identity_hash: str) -> bool:
        """Delete a single sticker. Returns ``True`` when a row was removed."""
        cur = self.provider.execute(
            "DELETE FROM user_stickers WHERE id = ? AND identity_hash = ?",
            (sticker_id, identity_hash),
        )
        return cur.rowcount > 0

    def delete_all_for_identity(self, identity_hash: str) -> int:
        """Delete every sticker (and dissociate packs) for an identity."""
        cur = self.provider.execute(
            "DELETE FROM user_stickers WHERE identity_hash = ?",
            (identity_hash,),
        )
        return cur.rowcount

    def delete_all_for_pack(self, pack_id: int, identity_hash: str) -> int:
        """Delete every sticker that belongs to ``pack_id``."""
        cur = self.provider.execute(
            "DELETE FROM user_stickers WHERE pack_id = ? AND identity_hash = ?",
            (pack_id, identity_hash),
        )
        return cur.rowcount

    def update_name(
        self,
        sticker_id: int,
        identity_hash: str,
        name: str | None,
    ) -> bool:
        """Update the user-friendly name of a sticker."""
        now = time.time()
        cur = self.provider.execute(
            """
            UPDATE user_stickers
            SET name = ?, updated_at = ?
            WHERE id = ? AND identity_hash = ?
            """,
            (name, now, sticker_id, identity_hash),
        )
        return cur.rowcount > 0

    def update_emoji(
        self,
        sticker_id: int,
        identity_hash: str,
        emoji: str | None,
    ) -> bool:
        """Update the optional emoji tag for a sticker."""
        now = time.time()
        cur = self.provider.execute(
            """
            UPDATE user_stickers
            SET emoji = ?, updated_at = ?
            WHERE id = ? AND identity_hash = ?
            """,
            (emoji, now, sticker_id, identity_hash),
        )
        return cur.rowcount > 0

    def assign_to_pack(
        self,
        sticker_id: int,
        identity_hash: str,
        pack_id: int | None,
    ) -> bool:
        """Move a sticker into a pack or back into the unpacked area."""
        now = time.time()
        cur = self.provider.execute(
            """
            UPDATE user_stickers
            SET pack_id = ?, updated_at = ?
            WHERE id = ? AND identity_hash = ?
            """,
            (pack_id, now, sticker_id, identity_hash),
        )
        return cur.rowcount > 0

    def insert(
        self,
        identity_hash: str,
        name: str | None,
        image_type: str,
        image_bytes: bytes,
        source_message_hash: str | None = None,
        *,
        pack_id: int | None = None,
        emoji: str | None = None,
        strict: bool = False,
        sort_order: int = 0,
    ) -> dict | None:
        """Insert a sticker. Returns ``None`` if a duplicate (by content hash).

        Validates the payload against the legacy or strict Telegram rules
        depending on ``strict``. Extracts and stores width/height/fps/duration
        metadata so the picker can render the sticker correctly without
        re-parsing.
        """
        if (
            self.count_for_identity(identity_hash)
            >= sticker_utils.MAX_STICKERS_PER_IDENTITY
        ):
            msg = "sticker_limit_reached"
            raise ValueError(msg)

        nt, ch = sticker_utils.validate_sticker_payload(
            image_bytes,
            image_type,
            strict=strict,
        )
        meta = sticker_utils.extract_metadata(nt, bytes(image_bytes))
        now = time.time()
        try:
            cur = self.provider.execute(
                """
                INSERT INTO user_stickers (
                    identity_hash, name, image_type, image_blob, content_hash,
                    source_message_hash, pack_id, emoji, width, height,
                    duration_ms, fps, is_animated, is_video, is_strict,
                    sort_order, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity_hash,
                    name,
                    nt,
                    image_bytes,
                    ch,
                    source_message_hash,
                    pack_id,
                    sticker_utils.sanitize_sticker_emoji(emoji),
                    meta.get("width"),
                    meta.get("height"),
                    meta.get("duration_ms"),
                    meta.get("fps"),
                    1 if meta.get("is_animated") else 0,
                    1 if meta.get("is_video") else 0,
                    1 if strict else 0,
                    int(sort_order or 0),
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError:
            return None

        new_id = cur.lastrowid
        row = self.provider.fetchone(
            f"""
            SELECT {_STICKER_SUMMARY_COLUMNS}
            FROM user_stickers
            WHERE id = ?
            """,
            (new_id,),
        )
        return dict(row) if row else None

    def export_payloads_for_identity(self, identity_hash: str) -> list[dict]:
        """Return base64-encoded payloads suitable for JSON export."""
        rows = self.provider.fetchall(
            """
            SELECT name, image_type, image_blob, source_message_hash, emoji
            FROM user_stickers
            WHERE identity_hash = ?
            ORDER BY id ASC
            """,
            (identity_hash,),
        )
        out = []
        for r in rows:
            blob = r["image_blob"]
            b64 = base64.b64encode(blob).decode("ascii")
            out.append(
                {
                    "name": r["name"],
                    "image_type": r["image_type"],
                    "image_bytes": b64,
                    "source_message_hash": r["source_message_hash"],
                    "emoji": r["emoji"],
                },
            )
        return out

    def export_payloads_for_pack(
        self,
        pack_id: int,
        identity_hash: str,
    ) -> list[dict]:
        """Return base64-encoded payloads for a single pack, in display order."""
        rows = self.provider.fetchall(
            """
            SELECT name, image_type, image_blob, emoji
            FROM user_stickers
            WHERE pack_id = ? AND identity_hash = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (pack_id, identity_hash),
        )
        out = []
        for r in rows:
            b64 = base64.b64encode(r["image_blob"]).decode("ascii")
            out.append(
                {
                    "name": r["name"],
                    "emoji": r["emoji"],
                    "image_type": r["image_type"],
                    "image_bytes": b64,
                },
            )
        return out

    def import_payloads(
        self,
        identity_hash: str,
        items: list[dict],
        *,
        replace_duplicates: bool,
        pack_id: int | None = None,
        strict: bool = False,
    ) -> dict:
        """Import a list of validated sticker payloads into the library."""
        imported = 0
        skipped_duplicates = 0
        skipped_invalid = 0
        errors: list[str] = []

        for i, item in enumerate(items):
            name = sticker_utils.sanitize_sticker_name(item.get("name"))
            it = item.get("image_type")
            b64 = item.get("image_bytes_b64")
            src = item.get("source_message_hash")
            emoji = sticker_utils.sanitize_sticker_emoji(item.get("emoji"))
            try:
                raw = base64.b64decode(b64, validate=False)
            except (ValueError, TypeError):
                skipped_invalid += 1
                errors.append(f"decode_failed_at_{i}")
                continue
            try:
                nt, ch = sticker_utils.validate_sticker_payload(raw, it, strict=strict)
            except ValueError as exc:
                skipped_invalid += 1
                errors.append(f"invalid_payload_at_{i}:{exc}")
                continue

            existing = self.provider.fetchone(
                "SELECT id FROM user_stickers WHERE identity_hash = ? AND content_hash = ?",
                (identity_hash, ch),
            )
            if existing:
                if not replace_duplicates:
                    skipped_duplicates += 1
                    continue
                self.provider.execute(
                    "DELETE FROM user_stickers WHERE identity_hash = ? AND content_hash = ?",
                    (identity_hash, ch),
                )

            if (
                self.count_for_identity(identity_hash)
                >= sticker_utils.MAX_STICKERS_PER_IDENTITY
            ):
                errors.append("sticker_limit_reached")
                break

            meta = sticker_utils.extract_metadata(nt, raw)
            now = time.time()
            try:
                self.provider.execute(
                    """
                    INSERT INTO user_stickers (
                        identity_hash, name, image_type, image_blob, content_hash,
                        source_message_hash, pack_id, emoji, width, height,
                        duration_ms, fps, is_animated, is_video, is_strict,
                        sort_order, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identity_hash,
                        name,
                        nt,
                        raw,
                        ch,
                        src if isinstance(src, str) else None,
                        pack_id,
                        emoji,
                        meta.get("width"),
                        meta.get("height"),
                        meta.get("duration_ms"),
                        meta.get("fps"),
                        1 if meta.get("is_animated") else 0,
                        1 if meta.get("is_video") else 0,
                        1 if strict else 0,
                        i,
                        now,
                        now,
                    ),
                )
                imported += 1
            except sqlite3.IntegrityError:
                skipped_duplicates += 1

        return {
            "imported": imported,
            "skipped_duplicates": skipped_duplicates,
            "skipped_invalid": skipped_invalid,
            "errors": errors,
        }
