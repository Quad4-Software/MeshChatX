---
name: electron-frozen-packaging
description: Frozen desktop spawn, --meshchatx-run-module re-entry, loading probes, crash recovery, external URL guards. Use when changing Electron main process or packaged helper spawn.
---

# Skill: electron-frozen-packaging

Package and recover the desktop shell correctly: frozen subprocess re-entry, loading probes, crash/offline DB restore, and external URL guards.

## When to use

- Changing Electron main process, backend spawn, or close / tray behaviour
- Spawning bots, rnsh, LXMFy, or other Python helpers from a packaged build
- Touching crash screens, offline recovery, or external link opening
- Changing in-window navigation, popouts, or preload IPC origin checks

## Frozen executable rules

- In frozen builds, `sys.executable` **is** MeshChatX.
- Never spawn `python -m …` or `python -c …` for bots, rnsh, LXMFy, or self-check probes from the packaged app.
- Use `--meshchatx-run-module <module>` so helpers re-enter the same binary without launching a second full app (storage lock collision).
- On Windows, Electron can start the backend through `--meshchatx-run-module meshchatx.src.backend.appcontainer_launcher` when `MESHCHAT_APPCONTAINER=1`. The launcher CreateProcess-es the real backend into an LPAC AppContainer. Orphan kill must use process-tree termination (`taskkill /T`) so both launcher and child exit. Default is off (direct backend spawn).

## Loading and navigation

- Loading shell probes `/api/v1/status`. `starting` is valid for early navigation (see `deferred-network-startup`).
- Parse local-backend URLs with `electron/shellOrigin.js`. Never `startsWith("http://127.0.0.1")`.
- Attach `will-navigate`, `will-redirect`, `will-frame-navigate`, and `setWindowOpenHandler` on `web-contents-created` so popouts get the same guards.
- Deny `will-attach-webview`. Deny `data:` in-window. Allow `blob:` only when the inner origin is the local backend.
- Preload `window.electron` IPC runs only for `isTrustedShellOrigin` (file loading.html/crash.html, `127.0.0.1`/`localhost` port 9337, trusted blobs).
- `safeExternalUrl` sends remaining http(s)/mailto to the OS browser. Do not replace the app window with external sites.
- Close behaviour (quit / tray / ask) persists per user choice. Guard re-entrancy on close.

## Crash / offline recovery

- Crash UI can list backups under `database-backups/` and `snapshots/`.
- Prefer newest non-`SUSPICIOUS` backup.
- Relaunch paths may pass `--auto-recover` / `--emergency`.

## Key files

- `electron/main.js`
- `electron/shellOrigin.js`
- `electron/preload.js`
- `electron/backendProcess.js`
- `electron/loadingStatusProbe.js`
- `electron/offlineRecovery.js`
- `electron/closeBehavior.js`
- `electron/safeExternalUrl.js`
- `meshchatx/meshchat.py` (`--meshchatx-run-module`)

## Verification

```bash
uv run pytest tests/backend/test_meshchatx_run_module.py -q --tb=short
pnpm exec vitest run --config vitest.electron.config.js tests/electron/mainHelpers.test.js tests/electron/safeExternalUrl.test.js
```

Prefer focused Electron unit tests under `tests/electron/` when present for the touched module.

URL origin allowlists: `.agents/skills/url-origin-allowlists/SKILL.md`.
