#!/usr/bin/env bash
# Build Windows portable + NSIS installers (electron-builder).
#
# When MESHCHATX_FRONTEND_PREBUILT=1 the script reuses the prebuilt
# meshchatx/public/ artifact downloaded from the reusable Frontend build
# workflow and only rebuilds the cx_Freeze backend. Otherwise it falls back to
# the full pnpm dist:windows pipeline (frontend + docs + backend).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

git config --global core.longpaths true 2>/dev/null || true

if [[ "${MESHCHATX_FRONTEND_PREBUILT:-0}" == "1" ]]; then
    if [[ ! -f "meshchatx/public/index.html" ]]; then
        echo "MESHCHATX_FRONTEND_PREBUILT=1 but meshchatx/public/index.html is missing." >&2
        echo "Download the frontend artifact into meshchatx/public/ before invoking this script." >&2
        exit 1
    fi
    pnpm run dist:windows-prebuilt
else
    pnpm run dist:windows
fi

bash scripts/ci/github-prune-electron-dist-staging.sh
