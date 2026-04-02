#!/usr/bin/env bash
# Lint and test (parity with: task lint && task test:all). Used by GitHub Actions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

poetry run ruff check .
poetry run ruff format --check .
pnpm run lint
poetry run pytest tests/backend --cov=meshchatx/src/backend -q --tb=short
pnpm run test -- --exclude tests/frontend/i18n.test.js
pnpm run test tests/frontend/i18n.test.js
poetry run pytest tests/backend/test_translator_handler.py
