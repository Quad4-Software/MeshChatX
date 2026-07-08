# SPDX-License-Identifier: 0BSD

from datetime import UTC, datetime

from .provider import DatabaseProvider


class NotificationSoundDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def get_all(self):
        return self.provider.fetchall(
            "SELECT * FROM notification_sounds ORDER BY created_at DESC",
        )

    def get_by_id(self, sound_id):
        return self.provider.fetchone(
            "SELECT * FROM notification_sounds WHERE id = ?",
            (sound_id,),
        )

    def get_primary(self):
        return self.provider.fetchone(
            "SELECT * FROM notification_sounds WHERE is_primary = 1",
        )

    def add(self, filename, storage_filename, display_name=None):
        now = datetime.now(UTC)
        if display_name is None:
            display_name = filename

        count = self.provider.fetchone(
            "SELECT COUNT(*) as count FROM notification_sounds",
        )["count"]
        is_primary = 1 if count == 0 else 0

        cursor = self.provider.execute(
            "INSERT INTO notification_sounds (filename, display_name, storage_filename, is_primary, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (filename, display_name, storage_filename, is_primary, now, now),
        )
        return cursor.lastrowid

    def update(self, sound_id, display_name=None, is_primary=None):
        now = datetime.now(UTC)
        if is_primary == 1:
            self.provider.execute(
                "UPDATE notification_sounds SET is_primary = 0, updated_at = ?",
                (now,),
            )

        if display_name is not None and is_primary is not None:
            self.provider.execute(
                "UPDATE notification_sounds SET display_name = ?, is_primary = ?, updated_at = ? WHERE id = ?",
                (display_name, is_primary, now, sound_id),
            )
        elif display_name is not None:
            self.provider.execute(
                "UPDATE notification_sounds SET display_name = ?, updated_at = ? WHERE id = ?",
                (display_name, now, sound_id),
            )
        elif is_primary is not None:
            self.provider.execute(
                "UPDATE notification_sounds SET is_primary = ?, updated_at = ? WHERE id = ?",
                (is_primary, now, sound_id),
            )

    def delete(self, sound_id):
        sound = self.get_by_id(sound_id)
        if sound and sound["is_primary"] == 1:
            self.provider.execute(
                "DELETE FROM notification_sounds WHERE id = ?",
                (sound_id,),
            )
            next_sound = self.provider.fetchone(
                "SELECT id FROM notification_sounds LIMIT 1",
            )
            if next_sound:
                self.update(next_sound["id"], is_primary=1)
        else:
            self.provider.execute(
                "DELETE FROM notification_sounds WHERE id = ?",
                (sound_id,),
            )
