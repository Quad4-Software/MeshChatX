#!/usr/bin/env bash
# Install Python (Poetry) and Node (pnpm) dependencies for native Electron builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export GIT_TERMINAL_PROMPT=0

python -m poetry install --no-interaction --no-ansi
pnpm install --frozen-lockfile
