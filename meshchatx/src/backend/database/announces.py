# SPDX-License-Identifier: 0BSD

import json
from datetime import UTC, datetime

from meshchatx.src.backend.favourites_layout import (
    NOMADNET_FAVOURITES_LAYOUT_KEY,
    normalize_favourites_layout,
)

from .provider import DatabaseProvider


class AnnounceDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def upsert_announce(self, data):
        if not isinstance(data, dict):
            data = dict(data)

        fields = [
            "destination_hash",
            "aspect",
            "identity_hash",
            "identity_public_key",
            "app_data",
            "rssi",
            "snr",
            "quality",
        ]
        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))

        update_parts = []
        for f in fields:
            if f == "destination_hash":
                continue
            if f == "app_data":
                update_parts.append(
                    "app_data = COALESCE(EXCLUDED.app_data, announces.app_data)",
                )
            else:
                update_parts.append(f"{f} = EXCLUDED.{f}")
        update_set = ", ".join(update_parts)

        query = (
            f"INSERT INTO announces ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?) "  # nosec: BAN-B608
            f"ON CONFLICT(destination_hash) DO UPDATE SET {update_set}, updated_at = EXCLUDED.updated_at"
        )

        params = [data.get(f) for f in fields]
        now = datetime.now(UTC)
        params.append(now)
        params.append(now)
        self.provider.execute(query, params)

    def trim_announces_for_aspect(self, aspect, max_rows):
        """Delete oldest rows for this aspect until at most max_rows remain.

        Announces that correspond to a favourited destination or to a saved
        contact are considered protected and are never deleted by this trim,
        even if the total count exceeds max_rows. This prevents purging
        of announces (and the path/identity context they provide) for
        favourited NomadNet nodes and for messaging contacts when storage
        limits are enforced.
        """
        if max_rows < 1 or not aspect:
            return
        row = self.provider.fetchone(
            "SELECT COUNT(*) AS c FROM announces WHERE aspect = ?",
            (aspect,),
        )
        count = row["c"] if row else 0
        excess = count - max_rows
        if excess <= 0:
            return
        self.provider.execute(
            """
            DELETE FROM announces WHERE id IN (
                SELECT a.id FROM announces a
                WHERE a.aspect = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM favourite_destinations f
                      WHERE f.destination_hash = a.destination_hash
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM contacts c
                      WHERE c.remote_identity_hash = a.identity_hash
                         OR c.lxmf_address = a.destination_hash
                         OR c.lxst_address = a.destination_hash
                  )
                ORDER BY a.updated_at ASC, a.id ASC
                LIMIT ?
            )
            """,
            (aspect, excess),
        )

    def get_announces(self, aspect=None, limit=None, offset=0):
        query = "SELECT * FROM announces"
        params = []
        if aspect:
            query += " WHERE aspect = ?"
            params.append(aspect)
        if limit is not None:
            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset or 0)])
        return self.provider.fetchall(query, params)

    def get_announces_for_identity_hashes(self, identity_hashes, aspects=None):
        """Return announce rows for many identity hashes, newest first."""
        if not identity_hashes:
            return []
        aspect_list = [a for a in (aspects or []) if isinstance(a, str) and a.strip()]
        if not aspect_list:
            return []
        hash_list = []
        seen = set()
        for raw in identity_hashes:
            if not isinstance(raw, str):
                continue
            h = raw.strip()
            if not h or h in seen:
                continue
            seen.add(h)
            hash_list.append(h)
        if not hash_list:
            return []
        chunk_size = 400
        out = []
        aspect_placeholders = ", ".join(["?"] * len(aspect_list))
        for start in range(0, len(hash_list), chunk_size):
            chunk = hash_list[start : start + chunk_size]
            hash_placeholders = ", ".join(["?"] * len(chunk))
            sql = f"""
                SELECT identity_hash, aspect, app_data, destination_hash, updated_at
                FROM announces
                WHERE identity_hash IN ({hash_placeholders})
                  AND aspect IN ({aspect_placeholders})
                ORDER BY updated_at DESC
            """
            out.extend(self.provider.fetchall(sql, [*chunk, *aspect_list]))
        return out

    def index_announces_by_identity_aspect(self, rows):
        index = {}
        for row in rows or []:
            ident = row.get("identity_hash")
            aspect = row.get("aspect")
            if not ident or not aspect:
                continue
            key = (ident, aspect)
            if key not in index:
                index[key] = row
        return index

    def get_announce_by_hash(self, destination_hash):
        return self.provider.fetchone(
            "SELECT * FROM announces WHERE destination_hash = ?",
            (destination_hash,),
        )

    def get_announces_by_identity_hash(self, identity_hash):
        return self.provider.fetchall(
            "SELECT * FROM announces WHERE identity_hash = ?",
            (identity_hash,),
        )

    def get_announce_count_by_aspect(self, aspect):
        row = self.provider.fetchone(
            "SELECT COUNT(*) as count FROM announces WHERE aspect = ?",
            (aspect,),
        )
        return row["count"] if row else 0

    def delete_all_announces(self, aspect=None):
        if aspect:
            self.provider.execute(
                "DELETE FROM announces WHERE aspect = ?",
                (aspect,),
            )
        else:
            self.provider.execute("DELETE FROM announces")

    def get_filtered_announces(
        self,
        aspect=None,
        search_term=None,
        identity_hash=None,
        destination_hash=None,
        limit=2500,
        offset=0,
    ):
        query = "SELECT * FROM announces WHERE 1=1"
        params = []
        if aspect:
            query += " AND aspect = ?"
            params.append(aspect)
        if identity_hash:
            query += " AND identity_hash = ?"
            params.append(identity_hash)
        if destination_hash:
            query += " AND destination_hash = ?"
            params.append(destination_hash)
        if search_term:
            query += " AND (destination_hash LIKE ? OR identity_hash LIKE ?)"
            like_term = f"%{search_term}%"
            params.extend([like_term, like_term])

        query += " ORDER BY updated_at DESC"

        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        return self.provider.fetchall(query, params)

    # Custom Display Names
    def upsert_custom_display_name(self, destination_hash, display_name):
        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO custom_destination_display_names (destination_hash, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = EXCLUDED.updated_at
        """,
            (destination_hash, display_name, now, now),
        )

    def get_custom_display_name(self, destination_hash):
        row = self.provider.fetchone(
            "SELECT display_name FROM custom_destination_display_names WHERE destination_hash = ?",
            (destination_hash,),
        )
        return row["display_name"] if row else None

    def delete_custom_display_name(self, destination_hash):
        self.provider.execute(
            "DELETE FROM custom_destination_display_names WHERE destination_hash = ?",
            (destination_hash,),
        )

    def get_all_custom_display_names(self):
        return self.provider.fetchall(
            "SELECT destination_hash, display_name FROM custom_destination_display_names",
        )

    # Favourites
    def upsert_favourite(
        self,
        destination_hash,
        display_name,
        aspect,
        identify_on_connect=None,
    ):
        from meshchatx.src.backend.favourite_display_names import (
            is_unknown_favourite_display_name,
        )

        now = datetime.now(UTC)
        preserve_unknown = is_unknown_favourite_display_name(display_name)
        identify_val = None
        if identify_on_connect is not None:
            identify_val = 1 if identify_on_connect else 0
        self.provider.execute(
            """
            INSERT INTO favourite_destinations (
                destination_hash, display_name, aspect, identify_on_connect,
                created_at, updated_at
            )
            VALUES (?, ?, ?, COALESCE(?, 0), ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET
                display_name = CASE
                    WHEN ? THEN favourite_destinations.display_name
                    ELSE EXCLUDED.display_name
                END,
                aspect = EXCLUDED.aspect,
                identify_on_connect = CASE
                    WHEN ? IS NULL THEN favourite_destinations.identify_on_connect
                    ELSE ?
                END,
                updated_at = EXCLUDED.updated_at
        """,
            (
                destination_hash,
                display_name,
                aspect,
                identify_val,
                now,
                now,
                1 if preserve_unknown else 0,
                identify_val,
                identify_val,
            ),
        )

    def get_favourite_by_destination_hash(self, destination_hash):
        return self.provider.fetchone(
            "SELECT * FROM favourite_destinations WHERE destination_hash = ?",
            (destination_hash,),
        )

    def should_identify_on_connect(self, destination_hash) -> bool:
        row = self.get_favourite_by_destination_hash(destination_hash)
        if row is None:
            return False
        try:
            return bool(row["identify_on_connect"])
        except (KeyError, IndexError, TypeError):
            return False

    def get_favourites(self, aspect=None):
        if aspect:
            return self.provider.fetchall(
                "SELECT * FROM favourite_destinations WHERE aspect = ?",
                (aspect,),
            )
        return self.provider.fetchall("SELECT * FROM favourite_destinations")

    def delete_favourite(self, destination_hash):
        self.provider.execute(
            "DELETE FROM favourite_destinations WHERE destination_hash = ?",
            (destination_hash,),
        )

    def delete_all_favourites(self, aspect=None):
        if aspect:
            self.provider.execute(
                "DELETE FROM favourite_destinations WHERE aspect = ?",
                (aspect,),
            )
        else:
            self.provider.execute("DELETE FROM favourite_destinations")

    def get_favourites_layout(self):
        row = self.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            (NOMADNET_FAVOURITES_LAYOUT_KEY,),
        )
        if not row or row["value"] in (None, ""):
            return None
        try:
            parsed = json.loads(row["value"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return normalize_favourites_layout(parsed)

    def set_favourites_layout(self, layout):
        from meshchatx.src.backend.favourites_layout import (
            MAX_LAYOUT_JSON_BYTES,
        )

        normalized = normalize_favourites_layout(layout)
        if normalized is None:
            msg = "invalid favourites layout"
            raise ValueError(msg)
        payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)
        if len(payload.encode("utf-8")) > MAX_LAYOUT_JSON_BYTES:
            msg = "favourites layout exceeds size limit"
            raise ValueError(msg)
        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO config (key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at
            """,
            (
                NOMADNET_FAVOURITES_LAYOUT_KEY,
                payload,
                now,
                now,
            ),
        )
        return normalized
