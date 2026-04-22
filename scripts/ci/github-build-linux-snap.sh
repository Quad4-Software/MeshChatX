#!/usr/bin/env bash
# Build a Snap via electron-forge's @electron-forge/maker-snap.
#
# Expects ``meshchatx/public/`` to already contain a prebuilt frontend bundle
# (downloaded from the reusable Frontend build workflow), so this script only
# rebuilds the cx_Freeze backend before running ``electron-forge make``.
#
# Required system packages (installed by the workflow):
#   - snapcraft (installed via ``snap install snapcraft --classic``)
#   - LXD or multipass when building outside ``--use-lxd``/``--destructive-mode``
#     (electron-forge invokes snapcraft itself; we set
#     ``SNAPCRAFT_BUILD_ENVIRONMENT=host`` so the snap is built directly on the
#     runner without needing a build VM).
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

SNAPCRAFT_BUILD_ENVIRONMENT="${SNAPCRAFT_BUILD_ENVIRONMENT:-host}" \
FORGE_MAKE_SNAP=1 \
    node scripts/electron-forge-local-tmp.js make --targets @electron-forge/maker-snap
