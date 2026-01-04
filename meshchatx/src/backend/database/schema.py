from .provider import DatabaseProvider


class DatabaseSchema:
    LATEST_VERSION = 34

    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def initialize(self):
        # Create core tables if they don't exist
        self._create_initial_tables()

        # Run migrations
        current_version = self._get_current_version()
        self.migrate(current_version)

    def _ensure_column(self, table_name, column_name, column_type):
        """Add a column to a table if it doesn't exist."""
        # First check if it exists using PRAGMA
        cursor = self.provider.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]

        if column_name not in columns:
            try:
                # SQLite has limitations on ALTER TABLE ADD COLUMN:
                # 1. Cannot add UNIQUE or PRIMARY KEY columns
                # 2. Cannot add columns with non-constant defaults (like CURRENT_TIMESTAMP)

                # Strip non-constant defaults if present for the ALTER TABLE statement
                stmt_type = column_type
                forbidden_defaults = [
                    "CURRENT_TIMESTAMP",
                    "CURRENT_TIME",
                    "CURRENT_DATE",
                ]
                for forbidden in forbidden_defaults:
                    if f"DEFAULT {forbidden}" in stmt_type.upper():
                        # Remove the DEFAULT part for the ALTER statement
                        import re

                        stmt_type = re.sub(
                            f"DEFAULT\\s+{forbidden}",
                            "",
                            stmt_type,
                            flags=re.IGNORECASE,
                        ).strip()

                # Use the connection directly to avoid any middle-ware issues
                self.provider.connection.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {stmt_type}"
                )
            except Exception as e:
                # Log but don't crash, we might be able to continue
                print(f"Failed to add column {column_name} to {table_name}: {e}")

    def _sync_table_columns(self, table_name, create_sql):
        """
        Parses a CREATE TABLE statement and ensures all columns exist in the actual table.
        This is a robust way to handle legacy tables that are missing columns.
        """
        # Find the first '(' and the last ')'
        start_idx = create_sql.find("(")
        end_idx = create_sql.rfind(")")

        if start_idx == -1 or end_idx == -1:
            return

        inner_content = create_sql[start_idx + 1 : end_idx]

        # Split by comma but ignore commas inside parentheses (e.g. DECIMAL(10,2))
        definitions = []
        depth = 0
        current = ""
        for char in inner_content:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1

            if char == "," and depth == 0:
                definitions.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip():
            definitions.append(current.strip())

        for definition in definitions:
            definition = definition.strip()
            # Skip table-level constraints
            if not definition or definition.upper().startswith(
                ("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK")
            ):
                continue

            parts = definition.split(None, 1)
            if not parts:
                continue

            column_name = parts[0].strip('"').strip("`").strip("[").strip("]")
            column_type = parts[1] if len(parts) > 1 else "TEXT"

            # Special case for column types that are already PRIMARY KEY
            if "PRIMARY KEY" in column_type.upper() and column_name.upper() != "ID":
                # We usually don't want to ALTER TABLE ADD COLUMN with PRIMARY KEY
                # unless it's the main ID which should already exist
                continue

            self._ensure_column(table_name, column_name, column_type)

    def _get_current_version(self):
        row = self.provider.fetchone(
            "SELECT value FROM config WHERE key = ?",
            ("database_version",),
        )
        if row:
            return int(row["value"])
        return 0

    def _create_initial_tables(self):
        # We create the config table first so we can track version
        config_sql = """
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.provider.execute(config_sql)
        self._sync_table_columns("config", config_sql)

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
                    peer_hash TEXT,
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
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(destination_hash, page_path)
                )
            """,
            "lxmf_forwarding_rules": """
                CREATE TABLE IF NOT EXISTS lxmf_forwarding_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
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
            "notification_viewed_state": """
                CREATE TABLE IF NOT EXISTS notification_viewed_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    last_viewed_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "lxmf_telemetry": """
                CREATE TABLE IF NOT EXISTS lxmf_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT,
                    timestamp REAL,
                    data BLOB,
                    received_from TEXT,
                    physical_link TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(destination_hash, timestamp)
                )
            """,
            "ringtones": """
                CREATE TABLE IF NOT EXISTS ringtones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    display_name TEXT,
                    storage_filename TEXT,
                    is_primary INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "contacts": """
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    remote_identity_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "notifications": """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    remote_hash TEXT,
                    title TEXT,
                    content TEXT,
                    is_viewed INTEGER DEFAULT 0,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "keyboard_shortcuts": """
                CREATE TABLE IF NOT EXISTS keyboard_shortcuts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_hash TEXT,
                    action TEXT,
                    keys TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identity_hash, action)
                )
            """,
            "map_drawings": """
                CREATE TABLE IF NOT EXISTS map_drawings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_hash TEXT,
                    name TEXT,
                    data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "lxmf_last_sent_icon_hashes": """
                CREATE TABLE IF NOT EXISTS lxmf_last_sent_icon_hashes (
                    destination_hash TEXT PRIMARY KEY,
                    icon_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "debug_logs": """
                CREATE TABLE IF NOT EXISTS debug_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    is_anomaly INTEGER DEFAULT 0,
                    anomaly_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
        }

        for table_name, create_sql in tables.items():
            self.provider.execute(create_sql)

            # Robust self-healing: Ensure existing tables have all modern columns
            self._sync_table_columns(table_name, create_sql)

            # Create indexes that were present
            if table_name == "announces":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_announces_aspect ON announces(aspect)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_announces_identity_hash ON announces(identity_hash)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_announces_updated_at ON announces(updated_at)",
                )
            elif table_name == "lxmf_messages":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_source_hash ON lxmf_messages(source_hash)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_destination_hash ON lxmf_messages(destination_hash)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_peer_hash ON lxmf_messages(peer_hash)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_timestamp ON lxmf_messages(timestamp)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_peer_ts ON lxmf_messages(peer_hash, timestamp)",
                )
            elif table_name == "blocked_destinations":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_blocked_destinations_hash ON blocked_destinations(destination_hash)",
                )
            elif table_name == "spam_keywords":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spam_keywords_keyword ON spam_keywords(keyword)",
                )
            elif table_name == "notification_viewed_state":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_notification_viewed_state_destination_hash ON notification_viewed_state(destination_hash)",
                )
                self.provider.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_viewed_state_dest_hash_unique ON notification_viewed_state(destination_hash)",
                )
            elif table_name == "lxmf_telemetry":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_telemetry_destination_hash ON lxmf_telemetry(destination_hash)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lxmf_telemetry_timestamp ON lxmf_telemetry(timestamp)",
                )
                self.provider.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_telemetry_dest_ts_unique ON lxmf_telemetry(destination_hash, timestamp)",
                )
            elif table_name == "debug_logs":
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_debug_logs_timestamp ON debug_logs(timestamp)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_debug_logs_level ON debug_logs(level)",
                )
                self.provider.execute(
                    "CREATE INDEX IF NOT EXISTS idx_debug_logs_anomaly ON debug_logs(is_anomaly)",
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
                "CREATE INDEX IF NOT EXISTS idx_archived_pages_destination_hash ON archived_pages(destination_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_archived_pages_page_path ON archived_pages(page_path)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_archived_pages_hash ON archived_pages(hash)",
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
                "CREATE INDEX IF NOT EXISTS idx_crawl_tasks_destination_hash ON crawl_tasks(destination_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_crawl_tasks_page_path ON crawl_tasks(page_path)",
            )

        if current_version < 9:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS lxmf_forwarding_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    identity_hash TEXT,
                    forward_to_hash TEXT,
                    source_filter_hash TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_rules_identity_hash ON lxmf_forwarding_rules(identity_hash)",
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
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_mappings_alias_hash ON lxmf_forwarding_mappings(alias_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_mappings_sender_hash ON lxmf_forwarding_mappings(original_sender_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_forwarding_mappings_recipient_hash ON lxmf_forwarding_mappings(final_recipient_hash)",
            )

        if current_version < 10:
            # Ensure unique constraints exist for ON CONFLICT clauses
            # SQLite doesn't support adding UNIQUE constraints via ALTER TABLE,
            # but a UNIQUE index works for ON CONFLICT.

            # Clean up duplicates before adding unique indexes
            self.provider.execute(
                "DELETE FROM announces WHERE id NOT IN (SELECT MAX(id) FROM announces GROUP BY destination_hash)",
            )
            self.provider.execute(
                "DELETE FROM crawl_tasks WHERE id NOT IN (SELECT MAX(id) FROM crawl_tasks GROUP BY destination_hash, page_path)",
            )
            self.provider.execute(
                "DELETE FROM custom_destination_display_names WHERE id NOT IN (SELECT MAX(id) FROM custom_destination_display_names GROUP BY destination_hash)",
            )
            self.provider.execute(
                "DELETE FROM favourite_destinations WHERE id NOT IN (SELECT MAX(id) FROM favourite_destinations GROUP BY destination_hash)",
            )
            self.provider.execute(
                "DELETE FROM lxmf_user_icons WHERE id NOT IN (SELECT MAX(id) FROM lxmf_user_icons GROUP BY destination_hash)",
            )
            self.provider.execute(
                "DELETE FROM lxmf_conversation_read_state WHERE id NOT IN (SELECT MAX(id) FROM lxmf_conversation_read_state GROUP BY destination_hash)",
            )
            self.provider.execute(
                "DELETE FROM lxmf_messages WHERE id NOT IN (SELECT MAX(id) FROM lxmf_messages GROUP BY hash)",
            )

            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_announces_destination_hash_unique ON announces(destination_hash)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_crawl_tasks_destination_path_unique ON crawl_tasks(destination_hash, page_path)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_custom_display_names_dest_hash_unique ON custom_destination_display_names(destination_hash)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_favourite_destinations_dest_hash_unique ON favourite_destinations(destination_hash)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_messages_hash_unique ON lxmf_messages(hash)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_user_icons_dest_hash_unique ON lxmf_user_icons(destination_hash)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_conversation_read_state_dest_hash_unique ON lxmf_conversation_read_state(destination_hash)",
            )

        if current_version < 11:
            # Add is_spam column to lxmf_messages if it doesn't exist
            try:
                self.provider.execute(
                    "ALTER TABLE lxmf_messages ADD COLUMN is_spam INTEGER DEFAULT 0",
                )
            except Exception:  # noqa: S110
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
                "CREATE INDEX IF NOT EXISTS idx_call_history_remote_hash ON call_history(remote_identity_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_history_timestamp ON call_history(timestamp)",
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
                "CREATE INDEX IF NOT EXISTS idx_voicemails_remote_hash ON voicemails(remote_identity_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_voicemails_timestamp ON voicemails(timestamp)",
            )

        if current_version < 14:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS notification_viewed_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT UNIQUE,
                    last_viewed_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_viewed_state_destination_hash ON notification_viewed_state(destination_hash)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_viewed_state_dest_hash_unique ON notification_viewed_state(destination_hash)",
            )

        if current_version < 15:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS lxmf_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_hash TEXT,
                    timestamp REAL,
                    data BLOB,
                    received_from TEXT,
                    physical_link TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(destination_hash, timestamp)
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_telemetry_destination_hash ON lxmf_telemetry(destination_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_telemetry_timestamp ON lxmf_telemetry(timestamp)",
            )
            self.provider.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_lxmf_telemetry_dest_ts_unique ON lxmf_telemetry(destination_hash, timestamp)",
            )

        if current_version < 16:
            try:
                self.provider.execute(
                    "ALTER TABLE lxmf_forwarding_rules ADD COLUMN name TEXT",
                )
            except Exception:  # noqa: S110
                pass

        if current_version < 17:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS ringtones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    display_name TEXT,
                    storage_filename TEXT,
                    is_primary INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        if current_version < 18:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    remote_identity_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_remote_identity_hash ON contacts(remote_identity_hash)",
            )

        if current_version < 19:
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_history_remote_name ON call_history(remote_identity_name)",
            )

        if current_version < 20:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    remote_hash TEXT,
                    title TEXT,
                    content TEXT,
                    is_viewed INTEGER DEFAULT 0,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_remote_hash ON notifications(remote_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp)",
            )

        if current_version < 21:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS keyboard_shortcuts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_hash TEXT,
                    action TEXT,
                    keys TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identity_hash, action)
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_keyboard_shortcuts_identity_hash ON keyboard_shortcuts(identity_hash)",
            )

        if current_version < 22:
            # Optimize fetching conversations and favorites
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_timestamp ON lxmf_messages(timestamp)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_favourite_destinations_aspect ON favourite_destinations(aspect)",
            )
            # Add index for faster searching in announces
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_announces_updated_at ON announces(updated_at)",
            )

        if current_version < 23:
            # Further optimize conversation fetching
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_conv_optim ON lxmf_messages(source_hash, destination_hash, timestamp DESC)",
            )
            # Add index for unread message filtering
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_state_incoming ON lxmf_messages(state, is_incoming)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_announces_aspect ON announces(aspect)",
            )

        if current_version < 24:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS call_recordings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remote_identity_hash TEXT,
                    remote_identity_name TEXT,
                    filename_rx TEXT,
                    filename_tx TEXT,
                    duration_seconds INTEGER,
                    timestamp REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_recordings_remote_hash ON call_recordings(remote_identity_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_call_recordings_timestamp ON call_recordings(timestamp)",
            )

        if current_version < 25:
            # Add docs_downloaded to config if not exists
            self.provider.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                ("docs_downloaded", "0"),
            )

        if current_version < 26:
            # Add initial_docs_download_attempted to config if not exists
            self.provider.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                ("initial_docs_download_attempted", "0"),
            )

        if current_version < 28:
            # Add preferred_ringtone_id to contacts
            try:
                self.provider.execute(
                    "ALTER TABLE contacts ADD COLUMN preferred_ringtone_id INTEGER DEFAULT NULL",
                )
            except Exception:  # noqa: S110
                pass

        if current_version < 29:
            # Performance optimization indexes
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_peer_hash ON lxmf_messages(peer_hash)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_timestamp ON lxmf_messages(timestamp)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_lxmf_messages_peer_ts ON lxmf_messages(peer_hash, timestamp)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_announces_updated_at ON announces(updated_at)",
            )

        if current_version < 30:
            # Add custom_image to contacts
            try:
                self.provider.execute(
                    "ALTER TABLE contacts ADD COLUMN custom_image TEXT DEFAULT NULL",
                )
            except Exception:  # noqa: S110
                pass

        if current_version < 31:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS lxmf_last_sent_icon_hashes (
                    destination_hash TEXT PRIMARY KEY,
                    icon_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        if current_version < 32:
            # Add tutorial_seen and changelog_seen_version to config
            self.provider.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                ("tutorial_seen", "false"),
            )
            self.provider.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                ("changelog_seen_version", "0.0.0"),
            )

        if current_version < 33:
            self.provider.execute("""
                CREATE TABLE IF NOT EXISTS debug_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    is_anomaly INTEGER DEFAULT 0,
                    anomaly_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_debug_logs_timestamp ON debug_logs(timestamp)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_debug_logs_level ON debug_logs(level)",
            )
            self.provider.execute(
                "CREATE INDEX IF NOT EXISTS idx_debug_logs_anomaly ON debug_logs(is_anomaly)",
            )

        if current_version < 34:
            # Add updated_at to crawl_tasks
            try:
                self.provider.execute(
                    "ALTER TABLE crawl_tasks ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
                )
            except Exception:  # noqa: S110
                pass

        # Update version in config
        self.provider.execute(
            """
            INSERT INTO config (key, value, created_at, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at
            """,
            ("database_version", str(self.LATEST_VERSION)),
        )
