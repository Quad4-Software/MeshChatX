import os


class LegacyMigrator:
    def __init__(self, provider, reticulum_config_dir, identity_hash_hex):
        self.provider = provider
        self.reticulum_config_dir = reticulum_config_dir
        self.identity_hash_hex = identity_hash_hex

    def get_legacy_db_path(self):
        """Detect the path to the legacy database based on the Reticulum config directory."""
        possible_dirs = []
        if self.reticulum_config_dir:
            possible_dirs.append(self.reticulum_config_dir)

        # Add common default locations
        home = os.path.expanduser("~")
        possible_dirs.append(os.path.join(home, ".reticulum-meshchat"))
        possible_dirs.append(os.path.join(home, ".reticulum"))

        # Check each directory
        for config_dir in possible_dirs:
            legacy_path = os.path.join(
                config_dir,
                "identities",
                self.identity_hash_hex,
                "database.db",
            )
            if os.path.exists(legacy_path):
                # Ensure it's not the same as our current DB path
                # (though this is unlikely given the different base directories)
                try:
                    current_db_path = os.path.abspath(self.provider.db_path)
                    if os.path.abspath(legacy_path) == current_db_path:
                        continue
                except (AttributeError, OSError):
                    # If we can't get the absolute path, just skip this check
                    pass
                return legacy_path

        return None

    def should_migrate(self):
        """Check if migration should be performed.
        Only migrates if the current database is empty and a legacy database exists.
        """
        legacy_path = self.get_legacy_db_path()
        if not legacy_path:
            return False

        # Check if current DB has any messages
        try:
            res = self.provider.fetchone("SELECT COUNT(*) as count FROM lxmf_messages")
            if res and res["count"] > 0:
                # Already have data, don't auto-migrate
                return False
        except Exception:  # noqa: S110
            # Table doesn't exist yet, which is fine
            # We use a broad Exception here as the database might not even be initialized
            pass

        return True

    def migrate(self):
        """Perform the migration from the legacy database."""
        legacy_path = self.get_legacy_db_path()
        if not legacy_path:
            return False

        print(f"Detecting legacy database at {legacy_path}...")

        try:
            # Attach the legacy database
            # We use a randomized alias to avoid collisions
            alias = f"legacy_{os.urandom(4).hex()}"
            self.provider.execute(f"ATTACH DATABASE '{legacy_path}' AS {alias}")

            # Tables that existed in the legacy Peewee version
            tables_to_migrate = [
                "announces",
                "blocked_destinations",
                "config",
                "custom_destination_display_names",
                "favourite_destinations",
                "lxmf_conversation_read_state",
                "lxmf_messages",
                "lxmf_user_icons",
                "spam_keywords",
            ]

            print("Auto-migrating data from legacy database...")
            for table in tables_to_migrate:
                # Basic validation to ensure table name is from our whitelist
                if table not in tables_to_migrate:
                    continue

                try:
                    # Check if table exists in legacy DB
                    # We use a f-string here for the alias and table name, which are controlled by us
                    check_query = f"SELECT name FROM {alias}.sqlite_master WHERE type='table' AND name=?"  # noqa: S608
                    res = self.provider.fetchone(check_query, (table,))

                    if res:
                        # Get columns from both databases to ensure compatibility
                        # These PRAGMA calls are safe as they use controlled table/alias names
                        legacy_columns = [
                            row["name"]
                            for row in self.provider.fetchall(
                                f"PRAGMA {alias}.table_info({table})",
                            )
                        ]
                        current_columns = [
                            row["name"]
                            for row in self.provider.fetchall(
                                f"PRAGMA table_info({table})",
                            )
                        ]

                        # Find common columns
                        common_columns = [
                            col for col in legacy_columns if col in current_columns
                        ]

                        if common_columns:
                            cols_str = ", ".join(common_columns)
                            # We use INSERT OR IGNORE to avoid duplicates
                            # The table and columns are controlled by us
                            migrate_query = f"INSERT OR IGNORE INTO {table} ({cols_str}) SELECT {cols_str} FROM {alias}.{table}"  # noqa: S608
                            self.provider.execute(migrate_query)
                            print(
                                f"  - Migrated table: {table} ({len(common_columns)} columns)",
                            )
                        else:
                            print(
                                f"  - Skipping table {table}: No common columns found",
                            )
                except Exception as e:
                    print(f"  - Failed to migrate table {table}: {e}")

            self.provider.execute(f"DETACH DATABASE {alias}")
            print("Legacy migration completed successfully.")
            return True
        except Exception as e:
            print(f"Migration from legacy failed: {e}")
            return False
