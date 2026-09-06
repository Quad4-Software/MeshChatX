#!/usr/bin/env bash
# Build macOS arm64 DMG via electron-builder. Unsigned CI build. Signing is disabled.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CSC_IDENTITY_AUTO_DISCOVERY=false
export MESHCHATX_SKIP_BACKEND_MANIFEST=1

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

ARCH=arm64 pnpm run build-backend

bash scripts/ci/github-verify-frozen-codec2.sh "$ROOT/build/exe/darwin-arm64"
bash scripts/ci/github-verify-frozen-umsgpack.sh "$ROOT/build/exe/darwin-arm64"
bash scripts/ci/github-verify-frozen-runtime.sh "$ROOT/build/exe/darwin-arm64"

pnpm exec electron-builder --mac --arm64 --config scripts/ci/electron-builder-mac-arm64.yml --publish=never

bash scripts/ci/github-prune-electron-dist-staging.sh
bash scripts/ci/github-verify-electron-dist.sh mac
