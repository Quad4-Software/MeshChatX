# Test conventions

Applies when editing `tests/**/*.{py,js}`.

- Backend: `tests/backend/test_*.py` with pytest + asyncio auto mode.
- Frontend: `tests/frontend/*.test.js` with vitest + `@vue/test-utils`.
- Mock `window.api` for page tests. Assert toasts when outcomes are user-visible.
- Prefer focused files over full suite unless the user asks for broad runs.
- Landlock tests that apply the sandbox must run in a subprocess (one restrict per process).
- Long-running / notification soak suites can hang. Prefer timeouts and avoid piping pytest through `tail` in agent shells.

## Oracle style (no soft fuzz)

Property and fuzz tests must assert an accept or reject outcome, not only that nothing crashed.

Refuse these patterns:

- Bare `except Exception: pass` around the code under test
- `never_raises` tests with no postcondition
- Asserting only that a result dict has an `"ok"` key without checking True or False
- Mocks that return the success path for every input under a security oracle

Prefer:

- Independent oracle: given input X, predict accept or reject, then assert the code matches
- Jail oracles: on success, resolved path stays under the allowed root
- Closed reason sets: on `ValueError`, the message is one of the known machine reasons
- Round-trip or shape invariants when the API is pure parsing

Full skill: `docs/agents/skills/test-oracles/SKILL.md`.
Path jail filesystem features: `docs/agents/skills/path-jail-local-fs/SKILL.md` and `docs/agents/conventions/path-jail.md`.
Exploratory bug hunting: `docs/agents/skills/exploratory-testing/SKILL.md`.

## HTTP and WS path-scanning contracts

Route and WS manifests are discovered from source text:

- HTTP: `tests/backend/http_api_contract_helpers.py` scans `meshchatx/meshchat.py` and `meshchatx/src/backend/http/**/*.py`
- WS: `tests/backend/ws_contract_helpers.py` scans the same trees plus `rns_link_manager.py` for link events

Fixtures:

- `tests/backend/fixtures/http_api_routes.json`
- `tests/backend/fixtures/ws_message_manifest.json`

Refresh only when the inventory intentionally changes:

```bash
UPDATE_HTTP_API_ROUTES=1 uv run pytest tests/backend/test_http_api_contract.py -k meshchat_http_routes_match_fixture
UPDATE_WS_MESSAGE_MANIFEST=1 uv run pytest tests/backend/test_ws_json_contracts.py -k manifest_matches_meshchat
```

JSON response schemas stay in `tests/backend/` (`api_json_contract_schemas.py`, `http_api_response_schemas.py`, registry files). See `docs/agents/module-ownership.md`.

## Extended Edge Case Tester (EECT) and Live Validation (LV)

- EECT packs live under `tests/backend/eect/packs/` and use marker `eect`.
- LV ladder lives under `tests/backend/eect/live/` and uses marker `live_validation`.
- Replay a failure with `MESHCHAT_EECT_SEED=<seed>` (printed on assert failure).
- Commands: `task test:eect`, `task test:lv:l0`, `MESHCHAT_LIVE_VALIDATION=1 task test:lv`.
- LV L2/L3 are opt-in (`MESHCHAT_LIVE_VALIDATION=1` or `MESHCHAT_LIVE_RETICULUM=1`). L0/L1 stay CI-safe.

## HTTP and WebSocket contract scanners

- HTTP route inventory: `tests/backend/http_api_contract_helpers.py` scans
  `meshchatx/meshchat.py` and all `meshchatx/src/backend/http/**/*.py`.
- WS message inventory: `tests/backend/ws_contract_helpers.py` scans the same trees
  (plus `rns_link_manager.py` for `rns.link.*` broadcasts).
- Refresh HTTP fixture only when routes intentionally change:
  `UPDATE_HTTP_API_ROUTES=1 uv run pytest tests/backend/test_http_api_contract.py -k meshchat_http_routes_match_fixture`
- Refresh WS fixture only when message types intentionally change:
  `UPDATE_WS_MESSAGE_MANIFEST=1 uv run pytest tests/backend/test_ws_json_contracts.py -k manifest_matches_meshchat`
- Domain ownership for routes vs schemas: `docs/agents/module-ownership.md`.
- Extraction workflow: `docs/agents/skills/meshchat-orchestration-split/SKILL.md`.
