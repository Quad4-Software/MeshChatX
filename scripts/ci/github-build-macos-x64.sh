#!/usr/bin/env bash
# Build a macOS x86_64 DMG via Wails desktop packaging using MacPorts for native deps.
# Runs on the GitHub-hosted macos-15-intel runner.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CSC_IDENTITY_AUTO_DISCOVERY=false
export MESHCHATX_SKIP_BACKEND_MANIFEST=1

pnpm install --frozen-lockfile
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

. scripts/ci/setup-wails3.sh

# x64-only package on a native Intel runner: darwin:package builds a
# universal binary via lipo, which needs an arm64-capable CGO toolchain
# that Intel runners do not have. Build amd64 natively instead and rename
# the dmg so it does not claim to be universal.
(
    cd desktop
    task darwin:build PRODUCTION=true ARCH=amd64
    task darwin:create:app:bundle
    task darwin:create:dmg
)
cd "$ROOT"

mkdir -p dist
dmg="$(ls desktop/bin/*-mac-universal.dmg 2>/dev/null | head -1)"
if [ -n "$dmg" ]; then
    mv "$dmg" "dist/$(basename "$dmg" | sed 's/mac-universal/mac-x64/')"
fi
ls -1 dist/

