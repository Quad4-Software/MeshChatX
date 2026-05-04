#!/usr/bin/env bash
# Build darwin-arm64 and darwin-x64 cx_Freeze backends, then electron-builder --mac --universal.
# On Apple Silicon, the x64 backend must be built with an x86_64 Python (e.g. Homebrew in /usr/local).
# Set PYTHON_CMD_X64 to that interpreter if Poetry's default env is arm64-only.
#
# Optional env vars:
#   MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO=1   Drop _miniaudio.abi3.so from both per-arch
#                                           backend trees before lipo. Use this when a
#                                           universal2 miniaudio wheel cannot be coerced
#                                           into a single-arch build on a given runner.
#                                           Audio decode falls back to wave + LXST/pyogg.
#   MESHCHATX_FRONTEND_PREBUILT=1           Reuse meshchatx/public/ instead of rebuilding.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# @electron/universal merges x64 and arm64 app bundles and requires every non-binary
# file present in both trees to have identical bytes. Per-arch backend-manifest.json
# contents always differ, so skip embedding it here; electron/main.js treats a missing
# manifest as "skip integrity check" (see verifyBackendIntegrity).
export MESHCHATX_SKIP_BACKEND_MANIFEST=1

pnpm run electron-postinstall
pnpm run version:sync
# Skip frontend rebuild when CI provides a prebuilt meshchatx/public artifact
# via the reusable Frontend build workflow. Local invocations leave the flag
# unset and continue to build everything from source.
if [[ "${MESHCHATX_FRONTEND_PREBUILT:-0}" != "1" ]]; then
    pnpm run build-frontend
    pnpm run build-docs
    pnpm run build-repository-wheels
else
    if [[ ! -f "meshchatx/public/index.html" ]]; then
        echo "MESHCHATX_FRONTEND_PREBUILT=1 but meshchatx/public/index.html is missing." >&2
        echo "Download the frontend artifact into meshchatx/public/ before invoking this script." >&2
        exit 1
    fi
    echo "Reusing prebuilt frontend assets in meshchatx/public/."
fi
cross-env ARCH=arm64 pnpm run build-backend
_arm_miniaudio="build/exe/darwin-arm64/lib/_miniaudio.abi3.so"
if [[ -f "$_arm_miniaudio" ]]; then
    _ft=$(file --brief --no-pad "$_arm_miniaudio" 2>/dev/null || true)
    if [[ "$_ft" == *x86_64* && "$_ft" != *arm64* ]]; then
        echo "darwin-arm64 cx_Freeze output has x86_64-only _miniaudio.abi3.so; universal lipo will fail." >&2
        echo "Rebuild miniaudio in the Poetry env (see scripts/ci/github-install-deps.sh) or fix compiler flags." >&2
        exit 1
    fi
fi
if [[ -n "${PYTHON_CMD_X64:-}" ]]; then
    cross-env ARCH=x64 PYTHON_CMD="$PYTHON_CMD_X64" pnpm run build-backend
else
    cross-env ARCH=x64 pnpm run build-backend
fi

bash scripts/thin-backend-mach-o.sh

bash scripts/unify-backend-plain-files.sh

exec pnpm exec electron-builder --mac --universal --publish=never
