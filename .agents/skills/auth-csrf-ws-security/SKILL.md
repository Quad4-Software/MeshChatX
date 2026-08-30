---
name: auth-csrf-ws-security
description: CSRF on mutating HTTP, window.api callers, and WebSocket mutator denylist. Use when adding POST routes, auth/password changes, or WS types that mutate state.
---

# Skill: auth-csrf-ws-security

Keep mutating HTTP behind CSRF and `window.api`. Never move security-boundary settings onto open WebSocket mutators.

## When to use

- Adding POST/PUT/PATCH/DELETE API routes or frontend callers
- Changing auth, password hash, CSRF, or session cookie behaviour
- Adding WebSocket message types that mutate state
- Touching `config.set` or settings that affect the HTTP security boundary

## HTTP rules

- Mutating `/api/v1` calls from the UI must use `window.api` / `apiClient.js` so CSRF headers attach.
- Raw `fetch(..., { method: "POST" })` against the API fails `tests/frontend/apiFetchGuard.test.js`.
- Prefer CSRF-protected HTTP for anything that changes auth, passwords, or exposure.

## WebSocket rules

Denylist (must not be set via `config.set` WS):

- `auth_enabled`
- `auth_password_hash`

When password auth is enabled, WS mutators and reads require an authenticated session. That includes:

- `config.set`
- `rns.link.open|identify|request|send|close`
- Nomad download / archive mutators and archive reads
- LXMF forwarding rule mutators and `lxmf.forwarding.rules.get`
- keyboard shortcut set/delete and `keyboard_shortcuts.get`

Only `ping` skips the session check. Unknown types require auth.

`/ws` and `/ws/telephone/audio` upgrades also require a same-authority `Origin` (missing Origin is allowed for non-browser clients on loopback, or when password auth is enabled; missing Origin is rejected on non-loopback binds without auth). Behind a trusted proxy, `X-Forwarded-Host` is accepted as the public authority.

Public / read / mutator classification lives in `WEBSOCKET_PUBLIC_TYPES`, `WEBSOCKET_READ_TYPES`, and `WEBSOCKET_MUTATOR_TYPES` in `websocket_config_guard.py`. Control types `ws.subscribe`, `ws.unsubscribe`, `sync.subscribe`, and `ws.caps` are public.

## Dangerous knobs

- `MESHCHAT_DISABLE_CSRF` is tests/dev only. Do not recommend it as a normal fix.
- Password reset is CLI/env: `--reset-password` / `MESHCHAT_RESET_PASSWORD=true`.

## Key files

- `meshchatx/src/frontend/js/apiClient.js`
- `meshchatx/src/frontend/js/csrfToken.js`
- `meshchatx/src/backend/csrf.py`
- `meshchatx/src/backend/websocket_config_guard.py`
- `docs/en/identity-and-security.md`

## Verification

```bash
uv run pytest tests/backend/test_websocket_config_security.py tests/backend/test_websocket_config_guard.py tests/backend/test_ws_origin_filesync_oracles.py -q --tb=short
pnpm exec vitest run tests/frontend/apiFetchGuard.test.js
```
