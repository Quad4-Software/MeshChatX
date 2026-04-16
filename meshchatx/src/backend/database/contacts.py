# SPDX-License-Identifier: 0BSD

from .provider import DatabaseProvider


class ContactsDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def add_contact(
        self,
        name,
        remote_identity_hash,
        lxmf_address=None,
        lxst_address=None,
        preferred_ringtone_id=None,
        custom_image=None,
        is_telemetry_trusted=0,
    ):
        self.provider.execute(
            """
            INSERT INTO contacts (name, remote_identity_hash, lxmf_address, lxst_address, preferred_ringtone_id, custom_image, is_telemetry_trusted)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(remote_identity_hash) DO UPDATE SET
                name = EXCLUDED.name,
                lxmf_address = COALESCE(EXCLUDED.lxmf_address, contacts.lxmf_address),
                lxst_address = COALESCE(EXCLUDED.lxst_address, contacts.lxst_address),
                preferred_ringtone_id = EXCLUDED.preferred_ringtone_id,
                custom_image = EXCLUDED.custom_image,
                is_telemetry_trusted = EXCLUDED.is_telemetry_trusted,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                name,
                remote_identity_hash,
                lxmf_address,
                lxst_address,
                preferred_ringtone_id,
                custom_image,
                is_telemetry_trusted,
            ),
        )

    def get_contacts(self, search=None, limit=100, offset=0):
        if search:
            return self.provider.fetchall(
                """
                SELECT * FROM contacts 
                WHERE name LIKE ? OR remote_identity_hash LIKE ? OR lxmf_address LIKE ? OR lxst_address LIKE ?
                ORDER BY name ASC LIMIT ? OFFSET ?
                """,
                (
                    f"%{search}%",
                    f"%{search}%",
                    f"%{search}%",
                    f"%{search}%",
                    limit,
                    offset,
                ),
            )
        return self.provider.fetchall(
            "SELECT * FROM contacts ORDER BY name ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def get_contacts_count(self, search=None):
        if search:
            row = self.provider.fetchone(
                """
                SELECT COUNT(*) as n FROM contacts
                WHERE name LIKE ? OR remote_identity_hash LIKE ? OR lxmf_address LIKE ? OR lxst_address LIKE ?
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            row = self.provider.fetchone("SELECT COUNT(*) as n FROM contacts")
        return row["n"] if row else 0

    def get_contact(self, contact_id):
        return self.provider.fetchone(
            "SELECT * FROM contacts WHERE id = ?",
            (contact_id,),
        )

    def update_contact(
        self,
        contact_id,
        name=None,
        remote_identity_hash=None,
        lxmf_address=None,
        lxst_address=None,
        preferred_ringtone_id=None,
        custom_image=None,
        clear_image=False,
        is_telemetry_trusted=None,
    ):
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if remote_identity_hash is not None:
            updates.append("remote_identity_hash = ?")
            params.append(remote_identity_hash)
        if lxmf_address is not None:
            updates.append("lxmf_address = ?")
            params.append(lxmf_address)
        if lxst_address is not None:
            updates.append("lxst_address = ?")
            params.append(lxst_address)
        if preferred_ringtone_id is not None:
            updates.append("preferred_ringtone_id = ?")
            params.append(preferred_ringtone_id)
        if is_telemetry_trusted is not None:
            updates.append("is_telemetry_trusted = ?")
            params.append(1 if is_telemetry_trusted else 0)
        if clear_image:
            updates.append("custom_image = NULL")
        elif custom_image is not None:
            updates.append("custom_image = ?")
            params.append(custom_image)

        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE contacts SET {', '.join(updates)} WHERE id = ?"  # noqa: S608
        params.append(contact_id)
        self.provider.execute(query, tuple(params))

    def delete_contact(self, contact_id):
        self.provider.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))

    def get_contact_by_identity_hash(self, remote_identity_hash):
        return self.provider.fetchone(
            "SELECT * FROM contacts WHERE remote_identity_hash = ? OR lxmf_address = ? OR lxst_address = ?",
            (remote_identity_hash, remote_identity_hash, remote_identity_hash),
        )
