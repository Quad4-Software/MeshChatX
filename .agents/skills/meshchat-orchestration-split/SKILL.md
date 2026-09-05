---
name: meshchat-orchestration-split
description: Extract HTTP routes and WS handlers under backend/http without behaviour change. Use when moving handlers among routes/<domain>.py, routes/<domain>/ packages, or ws/handlers_*.py.
---

# Skill: meshchat-orchestration-split

Extract or split HTTP routes and WebSocket handlers under `meshchatx/src/backend/http/`
without changing behaviour.

## When to use

- Splitting or moving handlers among `routes/<domain>.py` modules or `routes/<domain>/` packages
- Moving WS inbound dispatch pieces among `ws/handlers_*.py`
- Adding new HTTP endpoints or WS message types in the extracted layout
- Splitting fat managers into packages that re-export the same public class from the old import path

Also read:

- `.agents/module-ownership.md`
- `.agents/conventions/backend.md`
- `.agents/conventions/tests.md`

## Hard rules

1. Mechanical extract only. No renames, no error-map tweaks, no new logging in the same change as a move.
2. One concern per change: move or behaviour, never both.
3. Keep public entrypoints:
    - `from meshchatx.meshchat import ReticulumMeshChat, main`
    - `get_routes()` and `_define_routes(routes)` return shape
    - middleware order: `auth`, `mime_type`, `security`, `csrf`, `ip_allowlist`
    - `register_<domain>_routes` importable from `http.routes.<domain>`
4. Handlers use `app` where the original used `self`.
5. No new business logic in route modules. Parse, call manager or app method, return response.
6. Identity lifecycle and LXMF callbacks stay on `ReticulumMeshChat` until lifecycle packaging.
7. Follow inventory names in `.agents/module-ownership.md`. Do not invent alternate folders.
8. Domain splits start from existing `routes/<domain>.py` modules, `routes/<domain>/` packages,
   or residual shared helpers. Do not re-extract routes from `meshchat.py`.
9. One-shot extract scripts that rewrote `meshchat.py` were removed. Do not revive them.
10. When converting `routes/<domain>.py` to a package, delete the old `.py` file in the same
    change and keep `register_<domain>_routes` on the package `__init__.py`.
11. Do not slim `meshchat_names` imports in the same change as a structural split.
    Prefer a shared `_names.py` inside the package that re-exports the previous import block.

## Layout

Current:

```
meshchatx/src/backend/http/
  context.py
  errors.py
  live_names.py
  meshchat_names.py
  middleware.py
  register.py
  routes/<domain>.py          # small domains
  routes/<domain>/            # fat domains as packages
    __init__.py               # exports register_<domain>_routes
    _names.py                 # optional shared meshchat_names imports
    <slice>.py                # register_<domain>_<slice>_routes helpers
  routes/__init__.py
  ws/dispatch.py
  ws/handlers_*.py
```

Pattern (single file or package `__init__.py`):

```python
def register_status_routes(routes, app):
    @routes.get("/api/v1/status")
    async def status(request): ...
```

Package composition pattern:

```python
# routes/telephone/__init__.py
def register_telephone_routes(routes, app):
    register_telephone_session_routes(routes, app)
    register_telephone_history_routes(routes, app)
    # ...
```

`register.py` calls `register_extracted_routes`, which binds meshchat free names via
`live_names.inject_meshchat_names` so `patch("meshchatx.meshchat.<symbol>")` still applies.

Lazy-import `register_all_routes` from inside `_define_routes` so route modules load after
meshchat is initialized.

## Manager package splits

Fat managers under `meshchatx/src/backend/` may become packages that re-export the public
class from the previous module path (for example `plugin_manager.PluginManager` still
imports after `plugin_manager.py` becomes `plugin_manager/`). Mechanical move only.
Keep identity-scoped state rules and Landlock/SQLite constraints unchanged.

## Contract scanners

Scanners must cover:

- `meshchatx/meshchat.py`
- `meshchatx/src/backend/http/**/*.py`
- lifecycle modules for broadcast payloads where relevant

HTTP: `tests/backend/http_api_contract_helpers.py` (`extract_meshchat_http_routes`).

WS: `tests/backend/ws_contract_helpers.py` (inbound, direct responses, broadcast).

Update fixtures only when inventory intentionally changes:

```bash
UPDATE_HTTP_API_ROUTES=1 uv run pytest tests/backend/test_http_api_contract.py -k meshchat_http_routes_match_fixture
UPDATE_WS_MESSAGE_MANIFEST=1 uv run pytest tests/backend/test_ws_json_contracts.py -k manifest_matches_meshchat
```

## Verification

After each domain move:

```bash
uv run pytest tests/backend/test_http_api_contract.py \
  tests/backend/test_api_json_contracts.py \
  tests/backend/test_http_api_json_contracts_broad.py \
  tests/backend/test_ws_json_contracts.py -q --tb=short
```

Also run domain tests for the moved area and `task test:quick` at milestones.

Before declaring a large milestone done: `task test:backend` and `task test:frontend`.

## Compatibility patches

Tests often use `patch("meshchatx.meshchat.<symbol>")`. Keep those symbols importable from
`meshchatx.meshchat` (re-export if moved). Live name proxies live in `backend/http/live_names.py`.

`ReticulumMeshChat.on_websocket_data_received` is a one-line delegate to `http/ws/dispatch.py`.
