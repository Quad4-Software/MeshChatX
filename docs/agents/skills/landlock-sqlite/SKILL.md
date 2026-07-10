# Skill: landlock-sqlite

Landlock + SQLite conversation-load failures (temp_store, slim queries, memory pressure).

# MeshChatX Landlock + SQLite

## Symptoms

- `/api/v1/lxmf/conversations` or `/api/v1/notifications` return 500/503
- Logs show `sqlite3.OperationalError: unable to open database file`
- Happens after Landlock enables, often with large message `fields` / base64 blobs

## Root causes (priority order)

1. Worker-thread connections missing `PRAGMA temp_store=MEMORY` (`DatabaseProvider._configure_connection`)
2. Conversation SELECT pulling full `content` / `fields`
3. Memory-pressure switching to `temp_store=FILE` under Landlock
4. Identity context not ready (should be 503, not 500)

## Required behavior

- Default: `temp_store=MEMORY` on every new connection
- Landlock active + memory pressure: shrink cache/mmap, **keep MEMORY temp**
- Non-Landlock memory pressure may use FILE temp + storage-local `sqlite-tmp` TMPDIR
- List queries: `substr(content, 1, 240)` and SQL `instr` flags for attachments
- API: map OperationalError / unable-to-open / locked to **503** with retryable message

## Verification

```bash
uv run pytest tests/backend/test_sqlite_landlock_temp_store.py tests/backend/test_sqlite_memory_pressure.py tests/backend/test_landlock_sandbox.py -q
```

For live stress, run Landlock in a **subprocess** (sandbox applies once per process). Expect FILE temp complex queries to fail under Landlock. MEMORY must pass.

## Key files

- `meshchatx/src/backend/database/provider.py`
- `meshchatx/src/backend/database/__init__.py`
- `meshchatx/src/backend/memory_pressure.py`
- `meshchatx/src/backend/message_handler.py`
- `meshchatx/src/backend/landlock_sandbox.py`
- `meshchatx/meshchat.py` (conversations/notifications error mapping)
