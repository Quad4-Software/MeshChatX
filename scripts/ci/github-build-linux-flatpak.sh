#!/usr/bin/env bash
# Build a Flatpak via electron-builder (same stack as AppImage/deb/macOS/Windows CI).
#
# Expects meshchatx/public/ to already contain a prebuilt frontend bundle
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

# Flatpak commit ref-binding must match the OSTree branch we publish
# (testing / beta / stable). electron-builder defaults to "master", which
# makes flatpak install --from …-testing.flatpakref fail on pull.
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

DEBUG="${DEBUG:-@malept/flatpak-bundler*}" \
    pnpm run dist:flatpak-prebuilt -- -c.flatpak.branch="${branch}"

bash scripts/ci/github-verify-electron-dist.sh flatpak
