#!/usr/bin/env bash
# Remove electron-builder staging directories under dist/ (unpacked app trees).
# Installers (.exe, .dmg, .blockmap, latest.yml, etc.) stay at dist/ root for CI artifacts and releases.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d dist ]]; then
    exit 0
fi

promote_installers_from_staging() {
    local staging="$1"
    local file dest base

    while IFS= read -r -d '' file; do
        base="$(basename "$file")"
        dest="dist/${base}"
        if [[ -e "$dest" ]]; then
            echo "github-prune-electron-dist-staging.sh: keeping existing dist/${base}"
            rm -f "$file"
            continue
        fi
        echo "github-prune-electron-dist-staging.sh: promoting ${staging}/${base} -> dist/${base}"
        mv -f "$file" "$dest"
    done < <(
        find "$staging" -maxdepth 1 -type f \( \
            -name '*.dmg' -o \
            -name '*.blockmap' -o \
            \( -name '*.zip' ! -name 'library.zip' \) -o \
            \( -name '*.yml' ! -name '*.so.yml' \) -o \
            \( -name '*.yaml' ! -name '*.so.yaml' \) \
            \) -print0
    )
}

for name in win-unpacked linux-unpacked mac mac-arm64 mac-x64 mac-universal mac-universal-x64-temp mac-universal-arm64-temp; do
    if [[ -e "dist/${name}" ]]; then
        promote_installers_from_staging "dist/${name}"
        echo "github-prune-electron-dist-staging.sh: removing dist/${name}"
        rm -rf "dist/${name}"
    fi
done

while IFS= read -r -d '' stray; do
    echo "github-prune-electron-dist-staging.sh: removing stray dist/$(basename "$stray")"
    rm -f "$stray"
done < <(
    find dist -maxdepth 1 -type f \( -name 'library.zip' -o -name '*.so.yml' \) -print0 2>/dev/null || true
)
