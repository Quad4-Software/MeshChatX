# Skill: database-migrations-backups

Bump schema versions correctly, keep backups and snapshots safe, and never conflate identity-key restore with full database zip restore.

## When to use

- Changing SQLite schema or migrations
- Touching backup, snapshot, restore, or crash-recovery paths
- Adding tables / columns used by conversation or settings features

## Schema rules

- Engine is SQLite with explicit SQL. No ORM.
- Bump `LATEST_VERSION` in `meshchatx/src/backend/database/schema.py` and add a migration path.
- Test upgrade from an older version when the change is non-trivial.

## Backup and snapshot rules

- Backups skip `database-backups/` and `snapshots/` so a new zip does not nest itself (`BACKUP_SKIP_DIR_NAMES`).
- Suspicious shrink writes `backup-SUSPICIOUS-*.zip` and skips rotation. Do not treat that as a normal backup.
- Checkpoint WAL before zip snapshots when the live DB is open.
- Worker-thread connections must share `DatabaseProvider` pragmas (see `landlock-sqlite`).

## Two restore operations

| Goal                               | API / CLI                                       | Artifact                    |
| ---------------------------------- | ----------------------------------------------- | --------------------------- |
| Private key only                   | `POST /api/v1/identity/restore`                 | identity key bytes / `.bin` |
| History + settings + identity tree | `POST /api/v1/database/restore`, `--restore-db` | `.zip`                      |

Details for pickers and tutorial copy: `identity-restore`.

## Key files

- `meshchatx/src/backend/database/schema.py`
- `meshchatx/src/backend/database/__init__.py`
- `meshchatx/meshchat.py` (backup / restore routes, `prepare_for_database_restore`)
- `electron/offlineRecovery.js`

## Verification

```bash
uv run pytest tests/backend/test_database_snapshots.py tests/backend/test_schema_migration_upgrade.py -q --tb=short
```
