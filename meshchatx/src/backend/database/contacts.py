from .provider import DatabaseProvider


class ContactsDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def add_contact(self, name, remote_identity_hash):
        self.provider.execute(
            """
            INSERT INTO contacts (name, remote_identity_hash)
            VALUES (?, ?)
            ON CONFLICT(remote_identity_hash) DO UPDATE SET
                name = EXCLUDED.name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, remote_identity_hash),
        )

    def get_contacts(self, search=None, limit=100, offset=0):
        if search:
            return self.provider.fetchall(
                """
                SELECT * FROM contacts 
                WHERE name LIKE ? OR remote_identity_hash LIKE ? 
                ORDER BY name ASC LIMIT ? OFFSET ?
                """,
                (f"%{search}%", f"%{search}%", limit, offset),
            )
        return self.provider.fetchall(
            "SELECT * FROM contacts ORDER BY name ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def get_contact(self, contact_id):
        return self.provider.fetchone(
            "SELECT * FROM contacts WHERE id = ?",
            (contact_id,),
        )

    def update_contact(self, contact_id, name=None, remote_identity_hash=None):
        if name and remote_identity_hash:
            self.provider.execute(
                "UPDATE contacts SET name = ?, remote_identity_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, remote_identity_hash, contact_id),
            )
        elif name:
            self.provider.execute(
                "UPDATE contacts SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, contact_id),
            )
        elif remote_identity_hash:
            self.provider.execute(
                "UPDATE contacts SET remote_identity_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (remote_identity_hash, contact_id),
            )

    def delete_contact(self, contact_id):
        self.provider.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))

