from datetime import UTC, datetime

from .provider import DatabaseProvider


class MiscDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    # Blocked Destinations
    def add_blocked_destination(self, destination_hash):
        now = datetime.now(UTC)
        self.provider.execute(
            "INSERT OR IGNORE INTO blocked_destinations (destination_hash, created_at, updated_at) VALUES (?, ?, ?)",
            (destination_hash, now, now),
        )

    def is_destination_blocked(self, destination_hash):
        return (
            self.provider.fetchone(
                "SELECT 1 FROM blocked_destinations WHERE destination_hash = ?",
                (destination_hash,),
            )
            is not None
        )

    def get_blocked_destinations(self):
        return self.provider.fetchall("SELECT * FROM blocked_destinations")

    def delete_blocked_destination(self, destination_hash):
        self.provider.execute(
            "DELETE FROM blocked_destinations WHERE destination_hash = ?",
            (destination_hash,),
        )

    # Spam Keywords
    def add_spam_keyword(self, keyword):
        now = datetime.now(UTC)
        self.provider.execute(
            "INSERT OR IGNORE INTO spam_keywords (keyword, created_at, updated_at) VALUES (?, ?, ?)",
            (keyword, now, now),
        )

    def get_spam_keywords(self):
        return self.provider.fetchall("SELECT * FROM spam_keywords")

    def delete_spam_keyword(self, keyword_id):
        self.provider.execute("DELETE FROM spam_keywords WHERE id = ?", (keyword_id,))

    def check_spam_keywords(self, title, content):
        keywords = self.get_spam_keywords()
        search_text = (title + " " + content).lower()
        for kw in keywords:
            if kw["keyword"].lower() in search_text:
                return True
        return False

    # User Icons
    def update_lxmf_user_icon(
        self,
        destination_hash,
        icon_name,
        foreground_colour,
        background_colour,
    ):
        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO lxmf_user_icons (destination_hash, icon_name, foreground_colour, background_colour, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET 
                icon_name = EXCLUDED.icon_name, 
                foreground_colour = EXCLUDED.foreground_colour, 
                background_colour = EXCLUDED.background_colour, 
                updated_at = EXCLUDED.updated_at
        """,
            (
                destination_hash,
                icon_name,
                foreground_colour,
                background_colour,
                now,
                now,
            ),
        )

    def get_user_icon(self, destination_hash):
        return self.provider.fetchone(
            "SELECT * FROM lxmf_user_icons WHERE destination_hash = ?",
            (destination_hash,),
        )

    # Forwarding Rules
    def get_forwarding_rules(self, identity_hash=None, active_only=False):
        query = "SELECT * FROM lxmf_forwarding_rules WHERE 1=1"
        params = []
        if identity_hash:
            query += " AND (identity_hash = ? OR identity_hash IS NULL)"
            params.append(identity_hash)
        if active_only:
            query += " AND is_active = 1"
        return self.provider.fetchall(query, params)

    def create_forwarding_rule(
        self,
        identity_hash,
        forward_to_hash,
        source_filter_hash,
        is_active=True,
        name=None,
    ):
        now = datetime.now(UTC)
        self.provider.execute(
            "INSERT INTO lxmf_forwarding_rules (identity_hash, forward_to_hash, source_filter_hash, is_active, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                identity_hash,
                forward_to_hash,
                source_filter_hash,
                1 if is_active else 0,
                name,
                now,
                now,
            ),
        )

    def delete_forwarding_rule(self, rule_id):
        self.provider.execute(
            "DELETE FROM lxmf_forwarding_rules WHERE id = ?",
            (rule_id,),
        )

    def toggle_forwarding_rule(self, rule_id):
        self.provider.execute(
            "UPDATE lxmf_forwarding_rules SET is_active = NOT is_active WHERE id = ?",
            (rule_id,),
        )

    # Archived Pages
    def archive_page(self, destination_hash, page_path, content, page_hash):
        now = datetime.now(UTC)
        self.provider.execute(
            "INSERT INTO archived_pages (destination_hash, page_path, content, hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (destination_hash, page_path, content, page_hash, now),
        )

    def get_archived_page_versions(self, destination_hash, page_path):
        return self.provider.fetchall(
            "SELECT * FROM archived_pages WHERE destination_hash = ? AND page_path = ? ORDER BY created_at DESC",
            (destination_hash, page_path),
        )

    def get_archived_pages_paginated(self, destination_hash=None, query=None):
        sql = "SELECT * FROM archived_pages WHERE 1=1"
        params = []
        if destination_hash:
            sql += " AND destination_hash = ?"
            params.append(destination_hash)
        if query:
            like_term = f"%{query}%"
            sql += (
                " AND (destination_hash LIKE ? OR page_path LIKE ? OR content LIKE ?)"
            )
            params.extend([like_term, like_term, like_term])

        sql += " ORDER BY created_at DESC"
        return self.provider.fetchall(sql, params)

    def delete_archived_pages(self, destination_hash=None, page_path=None):
        if destination_hash and page_path:
            self.provider.execute(
                "DELETE FROM archived_pages WHERE destination_hash = ? AND page_path = ?",
                (destination_hash, page_path),
            )
        else:
            self.provider.execute("DELETE FROM archived_pages")

    # Crawl Tasks
    def upsert_crawl_task(
        self,
        destination_hash,
        page_path,
        status="pending",
        retry_count=0,
    ):
        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO crawl_tasks (destination_hash, page_path, status, retry_count, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(destination_hash, page_path) DO UPDATE SET 
                status = EXCLUDED.status, 
                retry_count = EXCLUDED.retry_count
        """,
            (destination_hash, page_path, status, retry_count, now),
        )

    def get_pending_crawl_tasks(self):
        return self.provider.fetchall(
            "SELECT * FROM crawl_tasks WHERE status = 'pending'",
        )

    def update_crawl_task(self, task_id, **kwargs):
        allowed_keys = {
            "destination_hash",
            "page_path",
            "status",
            "retry_count",
            "updated_at",
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_keys}

        if not filtered_kwargs:
            return

        set_clause = ", ".join([f"{k} = ?" for k in filtered_kwargs])
        params = list(filtered_kwargs.values())
        params.append(task_id)
        query = f"UPDATE crawl_tasks SET {set_clause} WHERE id = ?"  # noqa: S608
        self.provider.execute(query, params)

    def get_pending_or_failed_crawl_tasks(self, max_retries, max_concurrent):
        return self.provider.fetchall(
            "SELECT * FROM crawl_tasks WHERE status IN ('pending', 'failed') AND retry_count < ? LIMIT ?",
            (max_retries, max_concurrent),
        )

    def get_archived_page_by_id(self, archive_id):
        return self.provider.fetchone(
            "SELECT * FROM archived_pages WHERE id = ?",
            (archive_id,),
        )

    # Notifications
    def add_notification(self, type, remote_hash, title, content):
        now = datetime.now(UTC)
        timestamp = datetime.now(UTC).timestamp()
        self.provider.execute(
            "INSERT INTO notifications (type, remote_hash, title, content, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (type, remote_hash, title, content, timestamp, now),
        )

    def get_notifications(self, filter_unread=False, limit=50):
        query = "SELECT * FROM notifications"
        params = []
        if filter_unread:
            query += " WHERE is_viewed = 0"
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        return self.provider.fetchall(query, params)

    def mark_notifications_as_viewed(self, notification_ids=None):
        if notification_ids:
            placeholders = ", ".join(["?"] * len(notification_ids))
            self.provider.execute(
                f"UPDATE notifications SET is_viewed = 1 WHERE id IN ({placeholders})",
                notification_ids,
            )
        else:
            self.provider.execute("UPDATE notifications SET is_viewed = 1")

    def get_unread_notification_count(self):
        row = self.provider.fetchone(
            "SELECT COUNT(*) as count FROM notifications WHERE is_viewed = 0",
        )
        return row["count"] if row else 0

    # Keyboard Shortcuts
    def get_keyboard_shortcuts(self, identity_hash):
        return self.provider.fetchall(
            "SELECT * FROM keyboard_shortcuts WHERE identity_hash = ?",
            (identity_hash,),
        )

    def upsert_keyboard_shortcut(self, identity_hash, action, keys):
        now = datetime.now(UTC)
        self.provider.execute(
            """
            INSERT INTO keyboard_shortcuts (identity_hash, action, keys, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(identity_hash, action) DO UPDATE SET 
                keys = EXCLUDED.keys, 
                updated_at = EXCLUDED.updated_at
        """,
            (identity_hash, action, keys, now, now),
        )

    def delete_keyboard_shortcut(self, identity_hash, action):
        self.provider.execute(
            "DELETE FROM keyboard_shortcuts WHERE identity_hash = ? AND action = ?",
            (identity_hash, action),
        )
