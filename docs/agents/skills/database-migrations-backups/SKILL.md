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
- Heavy data backfills in migrations should skip when the target table is empty. Fresh `Database Initialization` benches create empty DBs and still run every migration step.

### Expand-only policy (release N)

- Prefer `CREATE TABLE`, `ADD COLUMN` with NULL or default, and indexes.
- Avoid `DROP TABLE`, `DROP COLUMN`, table renames, and destructive `DELETE FROM` in the same release that new app code depends on.
- Defer drops and renames to **N+2** (two-release lag).
- When `LATEST_VERSION` bumps, note the schema change in `CHANGELOG.md`.
- CI runs `scripts/ci/check_schema_migrations.py` on `schema.py` changes. Rare destructive steps need `# migration-safety: allow-destructive` on the same line.

## Backup and snapshot rules

- Backups skip `database-backups/` and `snapshots/` so a new zip does not nest itself (`BACKUP_SKIP_DIR_NAMES`).
- Suspicious shrink writes `backup-SUSPICIOUS-*.zip` and skips rotation. Do not treat that as a normal backup.
- Checkpoint WAL before zip snapshots when the live DB is open.
- Before applying schema upgrades (`current_version` below `LATEST_VERSION`), write `backup-pre-migrate-v*-to-v*.zip` under `database-backups/` unless `MESHCHAT_SKIP_PRE_MIGRATE_BACKUP=1`. Migration aborts if that backup fails.
- After migrate, `PRAGMA quick_check` and `SELECT 1` must pass before the version row is updated. Failures log `schema_migration ... status=failed` and block startup.
- Prune older `backup-pre-migrate-*.zip` files, keeping five by default (`MESHCHAT_PRE_MIGRATE_BACKUP_KEEP`, `0` disables pruning).
- `database_version` greater than `LATEST_VERSION` raises `DatabaseTooNewError` at startup.
- Worker-thread connections must share `DatabaseProvider` pragmas (see `landlock-sqlite`).
- One storage directory per running instance: `StorageLock` serializes migration and runtime (do not run two replicas on one `/config` volume).

## Fixture workflow

When `LATEST_VERSION` changes:

```bash
task schema-fixtures
```

This writes `tests/backend/fixtures/schema_versions/schema_v{N}.db` for latest, N-1, and N-2 plus `manifest.json` (manifest is committed, `*.db` files are gitignored and generated before backend tests).

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
- `scripts/ci/check_schema_migrations.py`
- `scripts/ci/schema_fixture_generate.py`

## Verification

```bash
uv run python scripts/ci/check_schema_migrations.py
uv run pytest tests/backend/test_database_snapshots.py tests/backend/test_schema_migration_upgrade.py tests/backend/test_schema_migration_matrix.py -q --tb=short
```
