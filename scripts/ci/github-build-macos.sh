#!/usr/bin/env bash
# Build macOS arm64 .app + dmg via the Wails desktop Taskfile. Unsigned CI
# build; signing/notarization are separate release steps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export MESHCHATX_SKIP_BACKEND_MANIFEST=1

pnpm run version:sync

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
bash scripts/ci/github-verify-frozen-bleak.sh "$ROOT/build/exe/darwin-arm64"

. scripts/ci/setup-wails3.sh
cd desktop && task darwin:package
cd "$ROOT"

mkdir -p dist
cp -f desktop/bin/*.dmg dist/ 2>/dev/null || true
ls -1 dist/
