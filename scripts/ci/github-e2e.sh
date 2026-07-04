#!/usr/bin/env bash
# Run a thin Playwright smoke suite in CI (backend + Vite dev server).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CI=1
export MESHCHAT_SKIP_STORAGE_LOCK=1
export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-18079}"
export E2E_VITE_HOST="${E2E_VITE_HOST:-127.0.0.1}"
export E2E_VITE_PORT="${E2E_VITE_PORT:-5173}"

pnpm exec playwright install chromium --with-deps

pnpm exec playwright test tests/e2e/smoke.spec.js
