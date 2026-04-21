#!/usr/bin/env bash
# Build darwin-arm64 and darwin-x64 cx_Freeze backends, then electron-builder --mac --universal.
# On Apple Silicon, the x64 backend must be built with an x86_64 Python (e.g. Homebrew in /usr/local).
# Set PYTHON_CMD_X64 to that interpreter if Poetry's default env is arm64-only.
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
else
    if [[ ! -f "meshchatx/public/index.html" ]]; then
        echo "MESHCHATX_FRONTEND_PREBUILT=1 but meshchatx/public/index.html is missing." >&2
        echo "Download the frontend artifact into meshchatx/public/ before invoking this script." >&2
        exit 1
    fi
    echo "Reusing prebuilt frontend assets in meshchatx/public/."
fi
cross-env ARCH=arm64 pnpm run build-backend
if [[ -n "${PYTHON_CMD_X64:-}" ]]; then
    cross-env ARCH=x64 PYTHON_CMD="$PYTHON_CMD_X64" pnpm run build-backend
else
    cross-env ARCH=x64 pnpm run build-backend
fi

# @electron/universal v2.x checks SHA equality for every non-Mach-O file
# and throws if any differ (no x64ArchFiles escape for PLAIN files).
# cx_Freeze's library.zip contains only architecture-independent Python
# bytecode; the per-arch native extensions (.dylib/.so) live outside the
# zip. The two zips differ solely in .pyc header timestamps and zip
# metadata, so copying one over the other is safe and makes the merge pass.
bash scripts/unify-backend-plain-files.sh

exec pnpm exec electron-builder --mac --universal --publish=never
