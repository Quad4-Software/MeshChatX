#!/usr/bin/env bash
# Build a Flatpak via electron-builder (same stack as AppImage/deb/macOS/Windows CI).
#
# Expects ``meshchatx/public/`` to already contain a prebuilt frontend bundle
# (downloaded from the reusable Frontend build workflow), so this script only
# rebuilds the cx_Freeze backend before running electron-builder.
#
# Required system packages (installed by the workflow):
#   - flatpak, flatpak-builder, elfutils (for eu-strip)
#   - org.freedesktop.Platform/Sdk//25.08
#   - org.electronjs.Electron2.BaseApp//25.08
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f "meshchatx/public/index.html" ]]; then
    echo "meshchatx/public/index.html is missing; download the prebuilt frontend artifact first." >&2
    exit 1
fi

export PLATFORM=linux
export MESHCHATX_FRONTEND_PREBUILT=1

pnpm run dist:flatpak-prebuilt

bash scripts/ci/github-verify-electron-dist.sh flatpak
