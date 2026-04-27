#!/usr/bin/env bash
# Remove electron-builder staging directories under dist/ (unpacked app trees).
# Installers (.exe, .dmg, .blockmap, latest.yml, etc.) stay at dist/ root for CI artifacts and releases.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d dist ]]; then
    exit 0
fi

for name in win-unpacked linux-unpacked mac mac-arm64 mac-x64 mac-universal; do
    if [[ -e "dist/${name}" ]]; then
        echo "github-prune-electron-dist-staging.sh: removing dist/${name}"
        rm -rf "dist/${name}"
    fi
done
