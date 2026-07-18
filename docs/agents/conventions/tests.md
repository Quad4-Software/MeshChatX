# Test conventions

Applies when editing `tests/**/*.{py,js}`.

- Backend: `tests/backend/test_*.py` with pytest + asyncio auto mode.
- Frontend: `tests/frontend/*.test.js` with vitest + `@vue/test-utils`.
- Mock `window.api` for page tests. Assert toasts when outcomes are user-visible.
- Prefer focused files over full suite unless the user asks for broad runs.
- Landlock tests that apply the sandbox must run in a subprocess (one restrict per process).
- Long-running / notification soak suites can hang. Prefer timeouts and avoid piping pytest through `tail` in agent shells.

## Extended Edge Case Tester (EECT) and Live Validation (LV)

- EECT packs live under `tests/backend/eect/packs/` and use marker `eect`.
- LV ladder lives under `tests/backend/eect/live/` and uses marker `live_validation`.
- Replay a failure with `MESHCHAT_EECT_SEED=<seed>` (printed on assert failure).
- Commands: `task test:eect`, `task test:lv:l0`, `MESHCHAT_LIVE_VALIDATION=1 task test:lv`.
- LV L2/L3 are opt-in (`MESHCHAT_LIVE_VALIDATION=1` or `MESHCHAT_LIVE_RETICULUM=1`). L0/L1 stay CI-safe.
