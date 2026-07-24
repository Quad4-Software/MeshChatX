# Skill: deferred-network-startup

Treat HTTP-up as distinct from RNS-ready. Gate UI on `/api/v1/status`, return 503 for retryable init failures, and contain RNS panic on Android.

## When to use

- Changing boot order, status payload, or loading screens
- Adding APIs that need identity / DB / RNS before answering
- Touching Electron loading probes or Android Chaquopy boot
- Debugging "app loads but mesh is dead" or early 500s during start

## Lifecycle facts

- HTTP can bind before RNS / identity finish.
- `/api/v1/status` reports `starting` / `ok` / `failed` with `stage` and `network_ready`.
- `starting` is normal, not an error.
- Electron loading probes accept HTTP 200 with `starting` or `ok`. Do not require `network_ready` before first navigation.
- Vue boot uses startup interpreters that can mount recovery UI when `failed` still allows degraded UI.
- A browser service worker may serve a cached app shell while `/api/v1/status` is unreachable. That is not `ui_ready`. Keep gating on status polling.

## API behaviour

- Prefer **503** with a retryable message when identity / DB / network is temporarily unavailable.
- Prefer opaque **500** only for unexpected failures after ready.
- CLI one-shots (`--self-check`, restore helpers) may still initialize synchronously.

## Android / RNS panic

- `RNS.panic()` must be contained (`rns_startup_recovery.py`). Uncaught `os._exit` kills the in-process Android Python host.
- Off-main-thread RNS init cannot register signals. Reinstall handlers on the main loop after ready.

## Key files

- `meshchatx/meshchat.py` (`/api/v1/status`, background RNS init)
- `meshchatx/src/frontend/js/networkStartupWait.js`
- `electron/loadingStatusProbe.js`
- `meshchatx/src/backend/rns_startup_recovery.py`
- `meshchatx/src/backend/reticulum_config_guard.py`

## Verification

```bash
uv run pytest tests/backend/test_rns_startup_recovery.py -q --tb=short
pnpm exec vitest run tests/frontend/networkStartupWait.test.js
uv run python -m meshchatx.meshchat --self-check
```
