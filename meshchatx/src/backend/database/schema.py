from .provider import DatabaseProvider


class DatabaseSchema:
    LATEST_VERSION = 13

    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def initialize(self):
        # Create core tables if they don't exist
        self._create_initial_tables()

        # Run migrations
        current_version = self._get_current_version()
        self.migrate(current_version)

    def _get_current_version(self):
        row = self.provider.fetchone(
            "SELECT value FROM config WHERE key = ?", ("database_version",)
        )
        if row:
            return int(row["value"])
        return 0

    def _create_initial_tables(self):
        # We create the config table first so we can track version
        self.provider.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Other essential tables that were present from version 1
        # Peewee automatically creates tables if they don't exist.
        # Here we define the full schema for all tables as they should be now.

        tables = {
            "announces": """
                CREATE TABLE IF NOT EXISTS announces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    aspect TEXT,
                    identity_hash TEXT,
                    identity_public_key TEXT,
                    app_data TEXT,
                    rssi INTEGER,
                    snr REAL,
                    quality REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "custom_destination_display_names": """
                CREATE TABLE IF NOT EXISTS custom_destination_display_names (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    display_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "favourite_destinations": """
                CREATE TABLE IF NOT EXISTS favourite_destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    display_name TEXT,
                    aspect TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "lxmf_messages": """
                CREATE TABLE IF NOT EXISTS lxmf_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE,
                    source_hash TEXT,
                    destination_hash TEXT,
                    state TEXT,
                    progress REAL,
                    is_incoming INTEGER,
                    method TEXT,
                    delivery_attempts INTEGER DEFAULT 0,
                    next_delivery_attempt_at REAL,
                    title TEXT,
                    content TEXT,
                    fields TEXT,
                    timestamp REAL,
                    rssi INTEGER,
                    snr REAL,
                    quality REAL,
                    is_spam INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "lxmf_conversation_read_state": """
                CREATE TABLE IF NOT EXISTS lxmf_conversation_read_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    last_read_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "lxmf_user_icons": """
                CREATE TABLE IF NOT EXISTS lxmf_user_icons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    icon_name TEXT,
                    foreground_colour TEXT,
                    background_colour TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "blocked_destinations": """
                CREATE TABLE IF NOT EXISTS blocked_destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "spam_keywords": """
                CREATE TABLE IF NOT EXISTS spam_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "archived_pages": """
                CREATE TABLE IF NOT EXISTS archived_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT,
                    page_path TEXT,
                    content TEXT,
                    hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "crawl_tasks": """
                CREATE TABLE IF NOT EXISTS crawl_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT,
                    page_path TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at DATETIME,
                    next_retry_at DATETIME,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(destination_hash, page_path)
                )
            """,
            "lxmf_forwarding_rules": """
                CREATE TABLE IF NOT EXISTS lxmf_forwarding_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_hash TEXT,
                    forward_to_hash TEXT,
                    source_filter_hash TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "lxmf_forwarding_mappings": """
                CREATE TABLE IF NOT EXISTS lxmf_forwarding_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alias_identity_private_key TEXT,
                    alias_hash TEXT UNIQUE,
                    original_sender_hash TEXT,
                    final_recipient_hash TEXT,
                    original_destination_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "call_history": """
                CREATE TABLE IF NOT EXISTS call_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remote_identity_hash TEXT,
                    remote_identity_name TEXT,
                    is_incoming INTEGER,
                    status TEXT,
                    duration_seconds INTEGER,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "voicemails": """
                CREATE TABLE IF NOT EXISTS voicemails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remote_identity_hash TEXT,
                    remote_identity_name TEXT,
                    filename TEXT,
                    duration_seconds INTEGER,
                    is_read INTEGER DEFAULT 0,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
        }

        for table_name, create_sql in tables.items():
            self.provider.execute(create_sql)
            # Create indexes that were present
            if table_name == "announces":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_announces_aspect ON announces(aspect)"
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_announces_identity_hash ON announces(identity_hash)"
                )
            elif table_name == "lxmf_messages":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_source_hash ON lxmf_messages(source_hash)"
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_destination_hash ON lxmf_messages(destination_hash)"
                )
            elif table_name == "blocked_destinations":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_blocked_destinations_hash ON blocked_destinations(destination_hash)"
                )
            elif table_name == "spam_keywords":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spam_keywords_keyword ON spam_keywords(keyword)"
                )

    def migrate(self, current_version):
        if current_version < 7:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS archived_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT,
                    page_path TEXT,
                    content TEXT,
                    hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_archived_pages_destination_hash ON archived_pages(destination_hash)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_archived_pages_page_path ON archived_pages(page_path)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_archived_pages_hash ON archived_pages(hash)"
            )

        if current_version < 8:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS crawl_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT,
                    page_path TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at DATETIME,
                    next_retry_at DATETIME,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_crawl_tasks_destination_hash ON crawl_tasks(destination_hash)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_crawl_tasks_page_path ON crawl_tasks(page_path)"
            )

        if current_version < 9:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS lxmf_forwarding_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_hash TEXT,
                    forward_to_hash TEXT,
                    source_filter_hash TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_rules_identity_hash ON lxmf_forwarding_rules(identity_hash)"
            )

            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS lxmf_forwarding_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alias_identity_private_key TEXT,
                    alias_hash TEXT UNIQUE,
                    original_sender_hash TEXT,
                    final_recipient_hash TEXT,
                    original_destination_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_mappings_alias_hash ON lxmf_forwarding_mappings(alias_hash)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_mappings_sender_hash ON lxmf_forwarding_mappings(original_sender_hash)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_mappings_recipient_hash ON lxmf_forwarding_mappings(final_recipient_hash)"
            )

        if current_version < 10:
            # Ensure unique constraints exist for ON CONFLICT clauses
            # SQLite doesn't support adding UNIQUE constraints via ALTER TABLE,
            # but a UNIQUE index works for ON CONFLICT.

            # Clean up duplicates before adding unique indexes
            self.provider.execute(
                "DELETE FROM announces WHERE id NOT IN (SELECT MAX(id) FROM announces GROUP BY destination_hash)"
            )
            self.provider.execute(
                "DELETE FROM crawl_tasks WHERE id NOT IN (SELECT MAX(id) FROM crawl_tasks GROUP BY destination_hash, page_path)"
            )
            self.provider.execute(
                "DELETE FROM custom_destination_display_names WHERE id NOT IN (SELECT MAX(id) FROM custom_destination_display_names GROUP BY destination_hash)"
            )
            self.provider.execute(
                "DELETE FROM favourite_destinations WHERE id NOT IN (SELECT MAX(id) FROM favourite_destinations GROUP BY destination_hash)"
            )
            self.provider.execute(
                "DELETE FROM lxmf_user_icons WHERE id NOT IN (SELECT MAX(id) FROM lxmf_user_icons GROUP BY destination_hash)"
            )
            self.provider.execute(
                "DELETE FROM lxmf_conversation_read_state WHERE id NOT IN (SELECT MAX(id) FROM lxmf_conversation_read_state GROUP BY destination_hash)"
            )
            self.provider.execute(
                "DELETE FROM lxmf_messages WHERE id NOT IN (SELECT MAX(id) FROM lxmf_messages GROUP BY hash)"
            )

            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_announces_destination_hash_unique ON announces(destination_hash)"
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_crawl_tasks_destination_path_unique ON crawl_tasks(destination_hash, page_path)"
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_custom_display_names_dest_hash_unique ON custom_destination_display_names(destination_hash)"
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_favourite_destinations_dest_hash_unique ON favourite_destinations(destination_hash)"
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_messages_hash_unique ON lxmf_messages(hash)"
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_user_icons_dest_hash_unique ON lxmf_user_icons(destination_hash)"
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_conversation_read_state_dest_hash_unique ON lxmf_conversation_read_state(destination_hash)"
            )

        if current_version < 11:
            # Add is_spam column to lxmf_messages if it doesn't exist
            try:
                self.provider.execute(
                    "ALTER TABLE lxmf_messages ADD COLUMN is_spam INTEGER DEFAULT 0"
                )
            except Exception:
                # Column might already exist if table was created with newest schema
                pass

        if current_version < 12:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS call_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remote_identity_hash TEXT,
                    remote_identity_name TEXT,
                    is_incoming INTEGER,
                    status TEXT,
                    duration_seconds INTEGER,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_history_remote_hash ON call_history(remote_identity_hash)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_history_timestamp ON call_history(timestamp)"
            )

        if current_version < 13:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS voicemails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remote_identity_hash TEXT,
                    remote_identity_name TEXT,
                    filename TEXT,
                    duration_seconds INTEGER,
                    is_read INTEGER DEFAULT 0,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_voicemails_remote_hash ON voicemails(remote_identity_hash)"
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_voicemails_timestamp ON voicemails(timestamp)"
            )

        # Update version in config
        self.provider.execute(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("database_version", str(self.LATEST_VERSION)),
        )
