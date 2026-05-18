#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Install MeshChatX dependencies from an offline bundle for air-gapped builds.

Run this on the air-gapped machine after extracting the offline bundle into
vendor/offline/ (or the project root).

Usage:
  bash scripts/install-offline.sh

This script:
  1. Finds the offline bundle directory
  2. Extracts node_modules/ from the bundle (if not already present)
  3. Exports cache paths for uv and electron-builder
  4. Runs 'make install' in offline mode

After install, build with:
  MESHCHATX_OFFLINE_BUILD=1 make build
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

BUNDLE=""
if [[ -d "${ROOT_DIR}/vendor/offline" ]]; then
    BUNDLE=$(find "${ROOT_DIR}/vendor/offline" -maxdepth 1 -type d -name 'meshchatx-offline-bundle-*' 2>/dev/null | head -n 1)
fi

if [[ -z "${BUNDLE}" ]]; then
    echo "No offline bundle found in ${ROOT_DIR}/vendor/offline/" >&2
    echo "Create one on an online machine with:" >&2
    echo "  bash scripts/create-offline-bundle.sh" >&2
    exit 1
fi

BUNDLE_NAME=$(basename "${BUNDLE}")
echo "Found offline bundle: ${BUNDLE_NAME}"

if [[ -d "node_modules" ]]; then
    echo "node_modules already exists. Skipping extraction."
else
    NM_TAR="${BUNDLE}/node_modules.tar.gz"
    if [[ ! -f "${NM_TAR}" ]]; then
        echo "Missing node_modules.tar.gz in bundle" >&2
        exit 1
    fi
    echo "Extracting node_modules from bundle..."
    tar xzf "${NM_TAR}"
    echo "node_modules extracted."
fi

export MESHCHATX_OFFLINE_BUILD=1
export UV_CACHE_DIR="${BUNDLE}/uv-cache"
export ELECTRON_BUILDER_CACHE="${BUNDLE}/electron-builder-cache"

echo ""
echo "Running offline install..."
make install

echo ""
echo "========================================"
echo "Offline install complete."
echo ""
echo "Build with:"
echo "  MESHCHATX_OFFLINE_BUILD=1 make build"
echo ""
echo "Or package with:"
echo "  MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux"
echo "========================================"
