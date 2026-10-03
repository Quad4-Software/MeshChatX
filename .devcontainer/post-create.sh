#!/bin/bash
# SPDX-License-Identifier: 0BSD
# Post-create setup for the MeshChatX devcontainer.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Installing pnpm"
npm install -g pnpm@12.7.0

echo "==> Installing uv"
curl -fsSL https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "==> Installing Task"
sh scripts/ci/setup-task.sh 3.49.1 || sudo sh scripts/ci/setup-task.sh 3.49.1

echo "==> Installing TinyGo"
TINYGO_VERSION=0.42.0
curl -fsSL -o /tmp/tinygo.tar.gz \
    "https://github.com/tinygo-org/tinygo/releases/download/v${TINYGO_VERSION}/tinygo${TINYGO_VERSION}.linux-amd64.tar.gz"
sudo tar -C /usr/local -xzf /tmp/tinygo.tar.gz
rm /tmp/tinygo.tar.gz
export PATH="/usr/local/tinygo/bin:$PATH"

echo "==> Installing Python deps"
uv venv .venv
uv pip install -e ".[dev]" --python .venv/bin/python

echo "==> Installing Node deps"
pnpm install --frozen-lockfile

echo "==> Building WASM artifacts"
node scripts/build-geo-wasm.mjs
node scripts/build-visualiser-wasm.mjs

echo "==> Fetching micron WASM"
node scripts/fetch-micron-wasm.mjs || echo "micron wasm fetch skipped (offline or missing)"

echo ""
echo "Dev container ready. Useful commands:"
echo "  task dev          - run backend + vite"
echo "  task test:quick   - fast test loop"
echo "  task test:ui:selfcheck - crawl all routes"
echo "  npm run typecheck - vue-tsc check"
