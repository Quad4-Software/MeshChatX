import hashlib

from .database import Database


class ArchiverManager:
    def __init__(self, db: Database):
        self.db = db

    def archive_page(
        self, destination_hash, page_path, content, max_versions=5, max_storage_gb=1
    ):
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Check if already exists
        existing = self.db.provider.fetchone(
            "SELECT id FROM archived_pages WHERE destination_hash = ? AND page_path = ? AND hash = ?",
            (destination_hash, page_path, content_hash),
        )
        if existing:
            return

        # Insert new version
        self.db.misc.archive_page(destination_hash, page_path, content, content_hash)

        # Enforce max versions per page
        versions = self.db.misc.get_archived_page_versions(destination_hash, page_path)
        if len(versions) > max_versions:
            # Delete older versions
            to_delete = versions[max_versions:]
            for version in to_delete:
                self.db.provider.execute(
                    "DELETE FROM archived_pages WHERE id = ?", (version["id"],)
                )

        # Enforce total storage limit (approximate)
        total_size_row = self.db.provider.fetchone(
            "SELECT SUM(LENGTH(content)) as total_size FROM archived_pages"
        )
        total_size = total_size_row["total_size"] or 0
        max_bytes = max_storage_gb * 1024 * 1024 * 1024

        while total_size > max_bytes:
            oldest = self.db.provider.fetchone(
                "SELECT id, LENGTH(content) as size FROM archived_pages ORDER BY created_at ASC LIMIT 1"
            )
            if oldest:
                self.db.provider.execute(
                    "DELETE FROM archived_pages WHERE id = ?", (oldest["id"],)
                )
                total_size -= oldest["size"]
            else:
                break
