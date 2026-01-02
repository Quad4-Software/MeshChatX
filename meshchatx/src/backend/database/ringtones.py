from datetime import UTC, datetime

from .provider import DatabaseProvider


class RingtoneDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def get_all(self):
        return self.provider.fetchall("SELECT * FROM ringtones ORDER BY created_at DESC")

    def get_by_id(self, ringtone_id):
        return self.provider.fetchone("SELECT * FROM ringtones WHERE id = ?", (ringtone_id,))

    def get_primary(self):
        return self.provider.fetchone("SELECT * FROM ringtones WHERE is_primary = 1")

    def add(self, filename, storage_filename, display_name=None):
        now = datetime.now(UTC)
        if display_name is None:
            display_name = filename

        # check if this is the first ringtone, if so make it primary
        count = self.provider.fetchone("SELECT COUNT(*) as count FROM ringtones")["count"]
        is_primary = 1 if count == 0 else 0

        cursor = self.provider.execute(
            "INSERT INTO ringtones (filename, display_name, storage_filename, is_primary, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (filename, display_name, storage_filename, is_primary, now, now),
        )
        return cursor.lastrowid

    def update(self, ringtone_id, display_name=None, is_primary=None):
        now = datetime.now(UTC)
        if is_primary == 1:
            # reset others
            self.provider.execute("UPDATE ringtones SET is_primary = 0, updated_at = ?", (now,))

        if display_name is not None and is_primary is not None:
            self.provider.execute(
                "UPDATE ringtones SET display_name = ?, is_primary = ?, updated_at = ? WHERE id = ?",
                (display_name, is_primary, now, ringtone_id),
            )
        elif display_name is not None:
            self.provider.execute(
                "UPDATE ringtones SET display_name = ?, updated_at = ? WHERE id = ?",
                (display_name, now, ringtone_id),
            )
        elif is_primary is not None:
            self.provider.execute(
                "UPDATE ringtones SET is_primary = ?, updated_at = ? WHERE id = ?",
                (is_primary, now, ringtone_id),
            )

    def delete(self, ringtone_id):
        # if deleting primary, make another one primary if exists
        ringtone = self.get_by_id(ringtone_id)
        if ringtone and ringtone["is_primary"] == 1:
            self.provider.execute("DELETE FROM ringtones WHERE id = ?", (ringtone_id,))
            next_ringtone = self.provider.fetchone("SELECT id FROM ringtones LIMIT 1")
            if next_ringtone:
                self.update(next_ringtone["id"], is_primary=1)
        else:
            self.provider.execute("DELETE FROM ringtones WHERE id = ?", (ringtone_id,))

