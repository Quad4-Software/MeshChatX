# SPDX-License-Identifier: 0BSD

import base64
import sqlite3
import time

from meshchatx.src.backend import sticker_utils


class UserStickersDAO:
    def __init__(self, provider):
        self.provider = provider

    def count_for_identity(self, identity_hash: str) -> int:
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM user_stickers WHERE identity_hash = ?",
            (identity_hash,),
        )
        return int(row["c"]) if row else 0

    def list_for_identity(self, identity_hash: str):
        return self.provider.fetchall(
            """
            SELECT id, identity_hash, name, image_type, length(image_blob) AS image_size,
                   content_hash, source_message_hash, created_at, updated_at
            FROM user_stickers
            WHERE identity_hash = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (identity_hash,),
        )

    def get_row(self, sticker_id: int, identity_hash: str):
        return self.provider.fetchone(
            """
            SELECT id, identity_hash, name, image_type, image_blob, content_hash,
                   source_message_hash, created_at, updated_at
            FROM user_stickers
            WHERE id = ? AND identity_hash = ?
            """,
            (sticker_id, identity_hash),
        )

    def delete(self, sticker_id: int, identity_hash: str) -> bool:
        cur = self.provider.execute(
            "DELETE FROM user_stickers WHERE id = ? AND identity_hash = ?",
            (sticker_id, identity_hash),
        )
        return cur.rowcount > 0

    def delete_all_for_identity(self, identity_hash: str) -> int:
        cur = self.provider.execute(
            "DELETE FROM user_stickers WHERE identity_hash = ?",
            (identity_hash,),
        )
        return cur.rowcount

    def update_name(
        self,
        sticker_id: int,
        identity_hash: str,
        name: str | None,
    ) -> bool:
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

    def insert(
        self,
        identity_hash: str,
        name: str | None,
        image_type: str,
        image_bytes: bytes,
        source_message_hash: str | None = None,
    ) -> dict | None:
        """Insert a sticker. Returns summary dict or None if duplicate (same content_hash)."""
        if (
            self.count_for_identity(identity_hash)
            >= sticker_utils.MAX_STICKERS_PER_IDENTITY
        ):
            msg = "sticker_limit_reached"
            raise ValueError(msg)

        nt, ch = sticker_utils.validate_sticker_payload(image_bytes, image_type)
        now = time.time()
        try:
            cur = self.provider.execute(
                """
                INSERT INTO user_stickers (
                    identity_hash, name, image_type, image_blob, content_hash,
                    source_message_hash, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity_hash,
                    name,
                    nt,
                    image_bytes,
                    ch,
                    source_message_hash,
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError:
            return None

        new_id = cur.lastrowid
        row = self.provider.fetchone(
            """
            SELECT id, identity_hash, name, image_type, length(image_blob) AS image_size,
                   content_hash, source_message_hash, created_at, updated_at
            FROM user_stickers
            WHERE id = ?
            """,
            (new_id,),
        )
        return dict(row) if row else None

    def export_payloads_for_identity(self, identity_hash: str) -> list[dict]:
        rows = self.provider.fetchall(
            """
            SELECT name, image_type, image_blob, source_message_hash
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
                },
            )
        return out

    def import_payloads(
        self,
        identity_hash: str,
        items: list[dict],
        *,
        replace_duplicates: bool,
    ) -> dict:
        imported = 0
        skipped_duplicates = 0
        skipped_invalid = 0
        errors: list[str] = []

        for i, item in enumerate(items):
            name = sticker_utils.sanitize_sticker_name(item.get("name"))
            it = item.get("image_type")
            b64 = item.get("image_bytes_b64")
            src = item.get("source_message_hash")
            try:
                raw = base64.b64decode(b64, validate=False)
            except (ValueError, TypeError):
                skipped_invalid += 1
                errors.append(f"decode_failed_at_{i}")
                continue
            try:
                nt, ch = sticker_utils.validate_sticker_payload(raw, it)
            except ValueError:
                skipped_invalid += 1
                errors.append(f"invalid_payload_at_{i}")
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

            now = time.time()
            try:
                self.provider.execute(
                    """
                    INSERT INTO user_stickers (
                        identity_hash, name, image_type, image_blob, content_hash,
                        source_message_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identity_hash,
                        name,
                        nt,
                        raw,
                        ch,
                        src if isinstance(src, str) else None,
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
