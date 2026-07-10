# Skill: electron-frozen-packaging

Package and recover the desktop shell correctly: frozen subprocess re-entry, loading probes, crash/offline DB restore, and external URL guards.

## When to use

- Changing Electron main process, backend spawn, or close / tray behaviour
- Spawning bots, rnsh, LXMFy, or other Python helpers from a packaged build
- Touching crash screens, offline recovery, or external link opening

## Frozen executable rules

- In frozen builds, `sys.executable` **is** MeshChatX.
- Never spawn `python -m …` for bots, rnsh, or LXMFy from the packaged app.
- Use `--meshchatx-run-module <module>` so helpers re-enter the same binary without launching a second full app (storage lock collision).

## Loading and navigation

- Loading shell probes `/api/v1/status`. `starting` is valid for early navigation (see `deferred-network-startup`).
- `will-navigate` / `safeExternalUrl` send http(s) to the OS browser. Do not replace the app window with external sites.
- Close behaviour (quit / tray / ask) persists per user choice. Guard re-entrancy on close.

## Crash / offline recovery

- Crash UI can list backups under `database-backups/` and `snapshots/`.
- Prefer newest non-`SUSPICIOUS` backup.
- Relaunch paths may pass `--auto-recover` / `--emergency`.

## Key files

- `electron/main.js`
- `electron/backendProcess.js`
- `electron/loadingStatusProbe.js`
- `electron/offlineRecovery.js`
- `electron/closeBehavior.js`
- `electron/safeExternalUrl.js`
- `meshchatx/meshchat.py` (`--meshchatx-run-module`)

## Verification

```bash
uv run pytest tests/backend/test_meshchatx_run_module.py -q --tb=short
pnpm exec vitest run tests/electron/ --passWithNoTests 2>/dev/null || true
```

Prefer focused Electron unit tests under `tests/electron/` when present for the touched module.
