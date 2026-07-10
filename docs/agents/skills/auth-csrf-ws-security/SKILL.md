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

When password auth is enabled, WS mutators require an authenticated session. That includes:

- `config.set`
- `rns.link.open|identify|request|send|close`
- Nomad download / archive mutators
- LXMF forwarding rule mutators
- keyboard shortcut set/delete

Public / read types stay limited. See `WEBSOCKET_PUBLIC_TYPES`, `WEBSOCKET_READ_TYPES`, and `WEBSOCKET_MUTATOR_TYPES` in `websocket_config_guard.py`.

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
uv run pytest tests/backend/test_websocket_config_security.py tests/backend/test_websocket_config_guard.py -q --tb=short
pnpm exec vitest run tests/frontend/apiFetchGuard.test.js
```
