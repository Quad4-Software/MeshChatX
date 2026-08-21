#!/usr/bin/env bash
# CI subset: page smoke + Lighthouse budgets on core routes with simulated data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CI=1
export MESHCHAT_SKIP_STORAGE_LOCK=1
export MESHCHAT_UI_CI=1
export MESHCHAT_UI_PROD="${MESHCHAT_UI_PROD:-1}"
export MESHCHAT_LH_SKIP_BUILD="${MESHCHAT_LH_SKIP_BUILD:-0}"
export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-18079}"
export E2E_VITE_HOST="${E2E_VITE_HOST:-127.0.0.1}"
export E2E_VITE_PORT="${E2E_VITE_PORT:-5173}"
export LH_DEBUG_PORT="${LH_DEBUG_PORT:-9222}"

pnpm exec playwright install chromium --with-deps

pnpm exec playwright test --config playwright.ui.config.js tests/ui/pages.smoke.spec.js
pnpm exec playwright test --config playwright.ui.config.js tests/ui/lighthouse.spec.js
