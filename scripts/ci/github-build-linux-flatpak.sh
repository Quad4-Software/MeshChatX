#!/usr/bin/env bash
# Build a Flatpak of the Wails desktop shell + frozen backend.
#
# Expects meshchatx/public/ to already contain a prebuilt frontend bundle
# (downloaded from the reusable Frontend build workflow), so this script only
# rebuilds the cx_Freeze backend before invoking flatpak-builder.
#
# Required system packages (installed by the workflow):
#   - flatpak, flatpak-builder, elfutils (for eu-strip)
#   - org.freedesktop.Platform/Sdk//25.08
# A Flatpak manifest covering the Go shell + backend must exist under
# packaging/flatpak/ (manifest.json); packaging files live there.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f "meshchatx/public/index.html" ]]; then
    echo "meshchatx/public/index.html is missing; download the prebuilt frontend artifact first." >&2
    exit 1
fi

export PLATFORM=linux
export MESHCHATX_FRONTEND_PREBUILT=1

if [[ -n "${FLATPAK_BRANCH:-}" ]]; then
    branch="${FLATPAK_BRANCH}"
elif [[ -n "${GITHUB_REF_NAME:-}" ]]; then
    branch="$(python3 "${ROOT}/scripts/ci/github_flatpak_channel.py" "${GITHUB_REF_NAME}")"
else
    branch="stable"
fi
case "$branch" in
    testing | beta | stable) ;;
    *)
        echo "Invalid Flatpak branch: ${branch}" >&2
        exit 1
        ;;
esac
echo "Building Flatpak with branch=${branch}"

bash scripts/ensure-flatpak-flathub-remote.sh

pnpm run version:sync
pnpm run build-backend

manifest="packaging/flatpak/manifest.json"
if [[ ! -f "$manifest" ]]; then
    echo "packaging/flatpak/manifest.json is missing; the Wails flatpak manifest has not been authored yet." >&2
    exit 1
fi

flatpak-builder --repo=repo --force-clean build-dir "$manifest"
flatpak build-bundle repo "reticulum-meshchatx-${branch}.flatpak" com.meshchatx.app
