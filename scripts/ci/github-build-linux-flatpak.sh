#!/usr/bin/env bash
# Build a Flatpak via electron-forge's @electron-forge/maker-flatpak.
#
# Expects ``meshchatx/public/`` to already contain a prebuilt frontend bundle
# (downloaded from the reusable Frontend build workflow), so this script only
# rebuilds the cx_Freeze backend before running ``electron-forge make``.
#
# Required system packages (installed by the workflow):
#   - flatpak, flatpak-builder, elfutils (for eu-strip)
#   - org.freedesktop.Platform/Sdk//25.08
#   - org.electronjs.Electron2.BaseApp//25.08
# ``electron-forge-local-tmp.js`` registers the Flathub user remote before Forge so
# ``@malept/flatpak-bundler`` can auto-install those refs when missing.
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

DEBUG="${DEBUG:-@malept/flatpak-bundler*,electron-installer-flatpak*}" \
FORGE_MAKE_FLATPAK=1 \
    node scripts/electron-forge-local-tmp.js make --targets @electron-forge/maker-flatpak
