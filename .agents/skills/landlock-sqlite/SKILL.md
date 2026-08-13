---
name: landlock-sqlite
description: Linux Landlock and Windows AppContainer with SQLite temp_store, plus subprocess and user-local CLI probes. Use when changing sandbox rules, conversation queries, or Popen of external binaries.
---

# Skill: landlock-sqlite

Landlock / Windows AppContainer + SQLite conversation-load failures (temp_store, slim queries, memory pressure). Also covers subprocess and user-local CLI breakage under Linux Landlock.

# MeshChatX FS sandbox + SQLite

## Symptoms

- `/api/v1/lxmf/conversations` or `/api/v1/notifications` return 500/503
- Logs show `sqlite3.OperationalError: unable to open database file`
- Happens after Landlock or Windows AppContainer enables, often with large message `fields` / base64 blobs

## Root causes (priority order)

1. Worker-thread connections missing `PRAGMA temp_store=MEMORY` (`DatabaseProvider._configure_connection`)
2. Conversation SELECT pulling full `content` / `fields`
3. Memory-pressure switching to `temp_store=FILE` under a filesystem sandbox
4. Identity context not ready (should be 503, not 500)

## Required behavior

- Default: `temp_store=MEMORY` on every new connection
- FS sandbox active (`landlock_active` or `appcontainer_active` / `fs_sandbox_active`) + memory pressure: shrink cache/mmap, **keep MEMORY temp**
- Non-sandbox memory pressure may use FILE temp + storage-local `sqlite-tmp` TMPDIR
- List queries: `substr(content, 1, 240)` and SQL `instr` flags for attachments
- API: map OperationalError / unable-to-open / locked to **503** with retryable message

## Subprocess and user-local tools (Linux Landlock)

### Symptoms

- Translator shows Argos as available but **no languages** after Refresh, or translation fails with `Permission denied`
- `argospm list` or `argos-translate` works in a normal shell but not inside MeshChatX
- PATH tools in `~/.local/bin` fail while `/usr/bin` tools work

### Root causes

1. Landlock read roots did not include pipx or user-local install paths (`~/.local/bin`, `~/.local/share/pipx`)
2. Argos Stanza needs **write** under `~/.local/share/argos-translate` (not read-only)
3. `TranslatorHandler` used Python `argostranslate` with zero packages and did not fall back to `argospm list`
4. Symlink wrappers in `~/.local/bin` that point outside allowed trees (not fixable by widening `~/.local/bin` alone)

### Required behavior

- `_collect_read_roots()` includes user-local CLI roots when present (`landlock_sandbox._collect_user_local_cli_roots`)
- `_collect_rw_roots()` includes `~/.local/share/argos-translate` when present
- New external-tool integrations: add roots and a probe in `tests/backend/test_landlock_integration_surfaces.py`

## Windows counterpart

- Module: `meshchatx/src/backend/appcontainer_sandbox.py`
- Launcher: `meshchatx/src/backend/appcontainer_launcher.py` via `--meshchatx-run-module`
- Electron win32 spawn uses the launcher only when `MESHCHAT_APPCONTAINER=1`

## Verification

```bash
uv run pytest tests/backend/test_sqlite_landlock_temp_store.py tests/backend/test_sqlite_memory_pressure.py tests/backend/test_landlock_sandbox.py tests/backend/test_landlock_integration_surfaces.py tests/backend/test_appcontainer_sandbox.py tests/backend/test_self_check.py -q
pnpm exec vitest run tests/frontend/i18n.test.js
bash scripts/ci/github-verify-frozen-sandbox.sh build/exe
```

For live stress, run Landlock in a **subprocess** (sandbox applies once per process). Expect FILE temp complex queries to fail under Landlock. MEMORY must pass. On Windows, confirm `appcontainer_active` via `/api/v1/server/security`. Headless self-check includes `FS Sandbox Modules` and requires AppContainer status fields on `/api/v1/server/security`.

## Key files

- `meshchatx/src/backend/database/provider.py`
- `meshchatx/src/backend/database/__init__.py`
- `meshchatx/src/backend/memory_pressure.py`
- `meshchatx/src/backend/landlock_sandbox.py`
- `meshchatx/src/backend/appcontainer_sandbox.py`
- `meshchatx/src/backend/appcontainer_launcher.py`
- `meshchatx/src/backend/seccomp_sandbox.py` (syscall denylist after Landlock)
- `meshchatx/src/backend/translator_handler.py` (Argos CLI and lib language listing)
- `tests/backend/landlock_integration_support.py`
- `tests/backend/test_landlock_integration_surfaces.py`
