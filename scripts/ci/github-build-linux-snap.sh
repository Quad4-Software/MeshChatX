#!/usr/bin/env bash
# Build a Snap via electron-forge's @electron-forge/maker-snap.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f "meshchatx/public/index.html" ]]; then
    echo "meshchatx/public/index.html is missing; download the prebuilt frontend artifact first." >&2
    exit 1
fi

export PLATFORM=linux

pnpm run electron-postinstall
pnpm run version:sync
pnpm run build-backend

export DEBUG="${DEBUG:+$DEBUG,}electron-installer-snap:snapcraft"

FORGE_MAKE_SNAP=1 node scripts/electron-forge-local-tmp.js make --targets @electron-forge/maker-snap
