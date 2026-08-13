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
- `_collect_read_roots()` includes `/sys` so pyserial can `open()` USB `idVendor`/`product` (stat alone is not enough)
- `apply_landlock_sandbox(extra_read_roots=...)` covers Sideband `command_plugins_path` when that dir exists at process start
- New external-tool integrations: add roots and a probe in `tests/backend/test_landlock_integration_surfaces.py`

## Serial ports and RNode (Linux Landlock)

### Symptoms

- Add Interface serial dropdown is empty with an RNode plugged in
- `/api/v1/comports` returns 500
- Logs show `TypeError: int() can't convert non-string with explicit base`

### Root cause

pyserial `list_ports_linux.SysFS` stats `/sys/class/tty/<name>/device` (Landlock allows this without a `/sys` rule), then `open()`s `idVendor`. That open fails, `read_line` returns None, and `int(None, 16)` raises. The comports route used to let that exception become HTTP 500.

### Required behavior

- `/sys` is a Landlock read root
- `list_serial_comports()` catches TypeError/ValueError/OSError and globs USB-like nodes (`ttyUSB`, `ttyACM`, `ttyAMA`, `rfcomm`)
- Probe: `test_landlock_allows_sysfs_tty_and_pyserial_comports`

## Custom interfaces, executable pages, plugins

In-tree copies already sit on Landlock roots:

- Custom RNS modules: `<reticulum_config_dir>/interfaces` (RW)
- Mesh Server executable pages: `<storage>/identities/<hash>/page_nodes/.../pages` (RW). Probe: `test_landlock_executable_page_script_spawn`
- MeshChatX plugins: `<storage>/plugins` (RW). Probe: `test_landlock_loads_python_plugin_from_storage`

These still fail under Landlock, by design:

- `location_cmd` or PipeInterface `command` whose binary is outside `/usr`, `~/.local/bin`, storage, and the Reticulum config dir (example: `~/bin/gps.sh`)
- Sideband `command_plugins_path` that did not exist yet when the process started (Landlock cannot add roots later). Restart after setting the path.
- Executable page scripts that write under `$HOME` or exec `/opt/...`

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
- `meshchatx/src/backend/serial_comports.py`
- `meshchatx/src/backend/appcontainer_sandbox.py`
- `meshchatx/src/backend/appcontainer_sandbox.py`
- `meshchatx/src/backend/appcontainer_launcher.py`
- `meshchatx/src/backend/seccomp_sandbox.py` (syscall denylist after Landlock)
- `meshchatx/src/backend/translator_handler.py` (Argos CLI and lib language listing)
- `tests/backend/landlock_integration_support.py`
- `tests/backend/test_landlock_integration_surfaces.py`
