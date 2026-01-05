from datetime import UTC, datetime

from .provider import DatabaseProvider


class AnnounceDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def upsert_announce(self, data):
        # Ensure data is a dict if it's a sqlite3.Row
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
        # These are safe as they are from a hardcoded list
        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        update_set = ", ".join(
            [f"{f} = EXCLUDED.{f}" for f in fields if f != "destination_hash"],
        )

        query = (
            f"INSERT INTO announces ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?) "  # noqa: S608
            f"ON CONFLICT(destination_hash) DO UPDATE SET {update_set}, updated_at = EXCLUDED.updated_at"
        )

        params = [data.get(f) for f in fields]
        now = datetime.now(UTC)
        params.append(now)
        params.append(now)
        self.provider.execute(query, params)

    def get_announces(self, aspect=None):
        if aspect:
            return self.provider.fetchall(
                "SELECT * FROM announces WHERE aspect = ?",
                (aspect,),
            )
        return self.provider.fetchall("SELECT * FROM announces")

    def get_announce_by_hash(self, destination_hash):
        return self.provider.fetchone(
            "SELECT * FROM announces WHERE destination_hash = ?",
            (destination_hash,),
        )

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
        limit=None,
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

    # Favourites
    def upsert_favourite(self, destination_hash, display_name, aspect):
        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO favourite_destinations (destination_hash, display_name, aspect, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET display_name = EXCLUDED.display_name, aspect = EXCLUDED.aspect, updated_at = EXCLUDED.updated_at
        """,
            (destination_hash, display_name, aspect, now, now),
        )

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
