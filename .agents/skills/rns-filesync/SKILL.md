---
name: rns-filesync
description: RNS FileSync shares, announces, permissions, and sync-root path jail. Use when changing the filesync handler, HTTP routes, announce interval, or in-app sync-tree CRUD.
---

# Skill: rns-filesync

Identity-scoped wrapper around vendored `rns_filesync.FileSyncService`. Peers are destination hashes. The sync directory is a path jail, not a convenient view of the host disk.

## When to use

- FileSync pages, share announce, peer permissions, or transfer status
- In-app browse/upload/mkdir/delete under the sync root
- Announce interval or service start/stop
- Anything that joins a client-supplied path onto the sync directory

Path jail details: `path-jail-local-fs` and `.agents/conventions/path-jail.md`.
Reference resolve helper: `rns_filesync_handler.py` (`_resolve_manager_path`).

## Hard rules

1. Jail CRUD to the configured `sync_directory` only. The folder picker that _chooses_ a sync root is a different, looser jail (identity storage with reserved tops blocked). Do not reuse the picker jail for tree/upload/delete.
2. Skip and refuse mutation of protocol sidecars (`.rns-filesync*`, `.rns-xfer*`).
3. `announce_interval` must be an integer `>= 10` seconds. Invalid values return `{"ok": False, "error": ...}` rather than throwing 500.
4. Upload cap for in-app manager uploads is `MANAGER_UPLOAD_MAX_BYTES` (64 MiB). That cap is the local control plane, not a mesh payload budget.
5. Large mesh transfers stay on FileSync/RNCP. Do not stuff files into LXMF chat fields.
6. Identity-scoped. Switching identities must tear down the service (see `identity-switch-teardown`).

## Key files

| Area             | Path                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------- |
| Handler          | `meshchatx/src/backend/rns_filesync_handler.py`                                          |
| HTTP             | `meshchatx/src/backend/http/routes/filesync.py`                                          |
| Vendored service | `vendor/rns_filesync/`                                                                   |
| UI               | `meshchatx/src/frontend/components/filesync/`                                            |
| Oracle tests     | `tests/backend/test_rns_filesync_security.py`, `tests/backend/test_path_jail_oracles.py` |

## Verification

```bash
uv run pytest tests/backend/test_rns_filesync_security.py tests/backend/test_path_jail_oracles.py -q --tb=short
```
