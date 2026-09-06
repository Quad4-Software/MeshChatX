---
name: test-loop
description: Focused verification with task/uv/pnpm without hanging shells. Use when running tests in an agent loop.
---

# Skill: test-loop

Focused verification with task/uv/pnpm without hanging shells.

# MeshChatX Test Loop

## Default order

1. Lint/format only the touched surface if needed
2. Focused unit tests for changed files
3. Broader suite only if asked or if cross-cutting

## Preferred commands

```bash
# Backend focused
uv run pytest tests/backend/test_<name>.py -q --tb=short

# Frontend focused
pnpm exec vitest run tests/frontend/<Name>.test.js

# Quick regression (full FE units + focused BE)
task test:quick

# Extended Edge Case Tester / Live Validation
task test:eect
task test:lv:l0
MESHCHAT_LIVE_VALIDATION=1 task test:lv

# Broader
task test:backend
task test:frontend

# UI page smoke / Lighthouse (Playwright + simulated data)
task test:ui:pages
# Always production-built assets (no Vite). Set MESHCHAT_LH_SKIP_BUILD=1 to reuse public/
task test:ui:lighthouse
MESHCHAT_UI_CI=1 task test:ui:lighthouse:ci
MESHCHAT_UI_PAGES=messages,contacts task test:ui:lighthouse
```

## Anti-hang rules

- Do not pipe long pytest runs through | tail in agent shells (blocks until process ends).
- Prefer --tb=short / -q and explicit file lists.
- Skip or isolate long_running / notification soak tests unless explicitly requested.
- Landlock apply tests: always subprocess.

## After UI edits

```bash
pnpm exec eslint <changed.vue> --fix
pnpm exec vitest run tests/frontend/<related>.test.js
```

## After identity / Landlock edits

Run the matching skill's verification section before claiming done: landlock-sqlite for the full Landlock/SQLite/AppContainer command set, identity-switch-teardown or identity-restore for identity flows.
