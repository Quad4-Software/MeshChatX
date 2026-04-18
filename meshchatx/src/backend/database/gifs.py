# SPDX-License-Identifier: 0BSD

import base64
import sqlite3
import time

from meshchatx.src.backend import gif_utils


class UserGifsDAO:
    """Per-identity library of user-uploaded GIFs.

    Mirrors :class:`UserStickersDAO` but exposes a ``usage_count``/``last_used_at``
    pair so the picker can order entries by most-used and the user can quickly
    reuse their favorite GIFs across chats.
    """

    def __init__(self, provider):
        self.provider = provider

    def count_for_identity(self, identity_hash: str) -> int:
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM user_gifs WHERE identity_hash = ?",
            (identity_hash,),
        )
        return int(row["c"]) if row else 0

    def list_for_identity(self, identity_hash: str):
        return self.provider.fetchall(
            """
            SELECT id, identity_hash, name, image_type, length(image_blob) AS image_size,
                   content_hash, source_message_hash, usage_count, last_used_at,
                   created_at, updated_at
            FROM user_gifs
            WHERE identity_hash = ?
            ORDER BY usage_count DESC, last_used_at DESC, updated_at DESC, id DESC
            """,
            (identity_hash,),
        )

    def get_row(self, gif_id: int, identity_hash: str):
        return self.provider.fetchone(
            """
            SELECT id, identity_hash, name, image_type, image_blob, content_hash,
                   source_message_hash, usage_count, last_used_at,
                   created_at, updated_at
            FROM user_gifs
            WHERE id = ? AND identity_hash = ?
            """,
            (gif_id, identity_hash),
        )

    def delete(self, gif_id: int, identity_hash: str) -> bool:
        cur = self.provider.execute(
            "DELETE FROM user_gifs WHERE id = ? AND identity_hash = ?",
            (gif_id, identity_hash),
        )
        return cur.rowcount > 0

    def delete_all_for_identity(self, identity_hash: str) -> int:
        cur = self.provider.execute(
            "DELETE FROM user_gifs WHERE identity_hash = ?",
            (identity_hash,),
        )
        return cur.rowcount

    def update_name(
        self,
        gif_id: int,
        identity_hash: str,
        name: str | None,
    ) -> bool:
        now = time.time()
        cur = self.provider.execute(
            """
            UPDATE user_gifs
            SET name = ?, updated_at = ?
            WHERE id = ? AND identity_hash = ?
            """,
            (name, now, gif_id, identity_hash),
        )
        return cur.rowcount > 0

    def record_usage(self, gif_id: int, identity_hash: str) -> bool:
        """Increment ``usage_count`` and refresh ``last_used_at`` for a GIF.

        Returns ``True`` when a row was updated, ``False`` when the GIF does
        not belong to the given identity.
        """
        now = time.time()
        cur = self.provider.execute(
            """
            UPDATE user_gifs
            SET usage_count = usage_count + 1, last_used_at = ?
            WHERE id = ? AND identity_hash = ?
            """,
            (now, gif_id, identity_hash),
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
        """Insert a GIF. Returns summary dict or ``None`` if duplicate (same content_hash)."""
        if self.count_for_identity(identity_hash) >= gif_utils.MAX_GIFS_PER_IDENTITY:
            msg = "gif_limit_reached"
            raise ValueError(msg)

        nt, ch = gif_utils.validate_gif_payload(image_bytes, image_type)
        now = time.time()
        try:
            cur = self.provider.execute(
                """
                INSERT INTO user_gifs (
                    identity_hash, name, image_type, image_blob, content_hash,
                    source_message_hash, usage_count, last_used_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
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
                   content_hash, source_message_hash, usage_count, last_used_at,
                   created_at, updated_at
            FROM user_gifs
            WHERE id = ?
            """,
            (new_id,),
        )
        return dict(row) if row else None

    def export_payloads_for_identity(self, identity_hash: str) -> list[dict]:
        rows = self.provider.fetchall(
            """
            SELECT name, image_type, image_blob, source_message_hash, usage_count
            FROM user_gifs
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
                    "usage_count": int(r["usage_count"] or 0),
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
            name = gif_utils.sanitize_gif_name(item.get("name"))
            it = item.get("image_type")
            b64 = item.get("image_bytes_b64")
            src = item.get("source_message_hash")
            usage = int(item.get("usage_count") or 0)
            if usage < 0:
                usage = 0
            try:
                raw = base64.b64decode(b64, validate=False)
            except (ValueError, TypeError):
                skipped_invalid += 1
                errors.append(f"decode_failed_at_{i}")
                continue
            try:
                nt, ch = gif_utils.validate_gif_payload(raw, it)
            except ValueError:
                skipped_invalid += 1
                errors.append(f"invalid_payload_at_{i}")
                continue

            existing = self.provider.fetchone(
                "SELECT id FROM user_gifs WHERE identity_hash = ? AND content_hash = ?",
                (identity_hash, ch),
            )
            if existing:
                if not replace_duplicates:
                    skipped_duplicates += 1
                    continue
                self.provider.execute(
                    "DELETE FROM user_gifs WHERE identity_hash = ? AND content_hash = ?",
                    (identity_hash, ch),
                )

            if (
                self.count_for_identity(identity_hash)
                >= gif_utils.MAX_GIFS_PER_IDENTITY
            ):
                errors.append("gif_limit_reached")
                break

            now = time.time()
            try:
                self.provider.execute(
                    """
                    INSERT INTO user_gifs (
                        identity_hash, name, image_type, image_blob, content_hash,
                        source_message_hash, usage_count, last_used_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                    """,
                    (
                        identity_hash,
                        name,
                        nt,
                        raw,
                        ch,
                        src if isinstance(src, str) else None,
                        usage,
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
