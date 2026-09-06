#!/usr/bin/env bash
# Build a macOS x86_64 DMG via electron-builder using MacPorts for native deps.
# Runs on the GitHub-hosted macos-15-intel runner.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CSC_IDENTITY_AUTO_DISCOVERY=false
export MESHCHATX_SKIP_BACKEND_MANIFEST=1

pnpm install --frozen-lockfile
pnpm run electron-postinstall
pnpm run version:sync

# Skip frontend rebuild when CI provides a prebuilt meshchatx/public artifact
# via the reusable Frontend build workflow.
if [[ "${MESHCHATX_FRONTEND_PREBUILT:-0}" != "1" ]]; then
    pnpm run build-frontend
    pnpm run build-docs
    pnpm run build-repository-wheels
else
    if [[ ! -f "meshchatx/public/index.html" ]]; then
        echo "MESHCHATX_FRONTEND_PREBUILT=1 but meshchatx/public/index.html is missing." >&2
        exit 1
    fi
    echo "Reusing prebuilt frontend assets in meshchatx/public/."
fi

export UV_PROJECT_ENVIRONMENT="${ROOT}/.venv-x64"
export PYTHON_CMD_X64="${UV_PROJECT_ENVIRONMENT}/bin/python"

ARCH=x64 PYTHON_CMD="${PYTHON_CMD_X64}" pnpm run build-backend

bash scripts/ci/github-verify-frozen-codec2.sh "$ROOT/build/exe/darwin-x64"
bash scripts/ci/github-verify-frozen-umsgpack.sh "$ROOT/build/exe/darwin-x64"
bash scripts/ci/github-verify-frozen-runtime.sh "$ROOT/build/exe/darwin-x64"

pnpm exec electron-builder --mac --x64 --config scripts/ci/electron-builder-mac-x64.yml --publish=never

bash scripts/ci/github-prune-electron-dist-staging.sh
bash scripts/ci/github-verify-electron-dist.sh mac
