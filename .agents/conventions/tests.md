# Test conventions

Applies when editing `tests/**/*.{py,js}`.

- Backend: `tests/backend/test_*.py` with pytest + asyncio auto mode.
- Frontend: `tests/frontend/*.test.js` with vitest + `@vue/test-utils`.
- Mock `window.api` for page tests. Assert toasts when outcomes are user-visible.
- Prefer focused files over full suite unless the user asks for broad runs.
- Landlock tests that apply the sandbox must run in a subprocess (one restrict per process).
- Shared runner: `tests/backend/landlock_integration_support.py` (`run_python_under_landlock`).
- Subprocess and user-local CLI probes: `tests/backend/test_landlock_integration_surfaces.py`.
- Unit tests for rules and ABI: `tests/backend/test_landlock_sandbox.py`.
- Long-running / notification soak suites can hang. Prefer timeouts and avoid piping pytest through `tail` in agent shells.

## Oracle style (no soft fuzz)

Property and fuzz tests must assert an accept or reject outcome, not only that nothing crashed.
Refuse bare `except Exception: pass`, `never_raises`-only tests, checking a result dict has an `"ok"` key without checking its value, and mocks that always succeed under a security oracle.
Prefer an independent oracle (predict accept or reject from the input, then assert the code matches), jail oracles (resolved path stays under the allowed root), closed reason sets (`ValueError` message is one of the known machine reasons), or round-trip invariants for pure parsing.

Full guidance and examples: `.agents/skills/test-oracles/SKILL.md`.
Path jail filesystem features: `.agents/skills/path-jail-local-fs/SKILL.md` and `.agents/conventions/path-jail.md`.
Exploratory bug hunting: `.agents/skills/exploratory-testing/SKILL.md`.

## Frontend mega-page ownership contracts

- Ownership inventory: `tests/frontend/fixtures/frontend_mega_page_ownership.json`
- Symbol continuity: `tests/frontend/fixtures/frontend_symbol_continuity/`
- Scanner tests: `tests/frontend/frontendOwnershipContract.test.js`
- Extract workflow: `.agents/skills/vue-mega-page-split/SKILL.md`
- Refresh ownership fixture only when inventory intentionally changes:
  `UPDATE_FRONTEND_OWNERSHIP=1 pnpm exec vitest run tests/frontend/frontendOwnershipContract.test.js -t ownership_fixture`

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

JSON response schemas stay in `tests/backend/` (`api_json_contract_schemas.py`, `http_api_response_schemas.py`, registry files). Domain ownership for routes vs schemas: `.agents/module-ownership.md`. Extraction workflow: `.agents/skills/meshchat-orchestration-split/SKILL.md`.

## Extended Edge Case Tester (EECT) and Live Validation (LV)

- EECT packs live under `tests/backend/eect/packs/` and use marker `eect`.
- LV ladder lives under `tests/backend/eect/live/` and uses marker `live_validation`.
- Replay a failure with `MESHCHAT_EECT_SEED=<seed>` (printed on assert failure).
- Commands: `task test:eect`, `task test:lv:l0`, `MESHCHAT_LIVE_VALIDATION=1 task test:lv`.
- LV L2/L3 are opt-in (`MESHCHAT_LIVE_VALIDATION=1` or `MESHCHAT_LIVE_RETICULUM=1`). L0/L1 stay CI-safe.
