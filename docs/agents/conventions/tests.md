# Test conventions

Applies when editing `tests/**/*.{py,js}`.

- Backend: `tests/backend/test_*.py` with pytest + asyncio auto mode.
- Frontend: `tests/frontend/*.test.js` with vitest + `@vue/test-utils`.
- Mock `window.api` for page tests. Assert toasts when outcomes are user-visible.
- Prefer focused files over full suite unless the user asks for broad runs.
- Landlock tests that apply the sandbox must run in a subprocess (one restrict per process).
- Long-running / notification soak suites can hang. Prefer timeouts and avoid piping pytest through `tail` in agent shells.
