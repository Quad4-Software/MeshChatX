#!/usr/bin/env bash
# Fail when expected Electron installer outputs are missing under dist/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

platform="${1:?usage: $0 mac|win|flatpak}"

if [[ ! -d dist ]]; then
    echo "dist/ is missing after electron-builder" >&2
    exit 1
fi

shopt -s nullglob

case "$platform" in
    mac)
        dmgs=(dist/*.dmg dist/mac/*.dmg dist/mac-universal/*.dmg dist/mac-arm64/*.dmg dist/mac-x64/*.dmg)
        if [[ ${#dmgs[@]} -eq 0 ]]; then
            echo "No macOS .dmg under dist/" >&2
            find dist -maxdepth 4 -type f 2>/dev/null | head -80 >&2 || true
            exit 1
        fi
        printf 'macOS DMG: %s\n' "${dmgs[@]}"
        ;;
    win)
        exes=(dist/*.exe)
        if [[ ${#exes[@]} -eq 0 ]]; then
            echo "No Windows .exe under dist/" >&2
            find dist -maxdepth 4 -type f 2>/dev/null | head -80 >&2 || true
            exit 1
        fi
        printf 'Windows installer: %s\n' "${exes[@]}"
        ;;
    flatpak)
        bundles=(dist/*.flatpak)
        if [[ ${#bundles[@]} -eq 0 ]]; then
            echo "No .flatpak under dist/" >&2
            find dist -maxdepth 4 -type f 2>/dev/null | head -80 >&2 || true
            exit 1
        fi
        printf 'Flatpak bundle: %s\n' "${bundles[@]}"
        ;;
    *)
        echo "unknown platform: ${platform}" >&2
        exit 1
        ;;
esac
