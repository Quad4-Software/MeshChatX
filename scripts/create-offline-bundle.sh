#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Create an offline bundle for air-gapped (zero-network) builds.

This script downloads and caches everything needed to build MeshChatX without
any network access. Run it on an online machine, then transfer the resulting
vendor/offline/ directory to your air-gapped build host.

Usage:
  bash scripts/create-offline-bundle.sh [options]

Options:
  --warm-packaging         Pre-download electron-builder packaging tools
                           (appimagetool, app-builder, etc.) by running a
                           dummy Linux build. Increases bundle size.
  --out-dir PATH           Output directory (default: vendor/offline)
  -h, --help               Show this help

Prerequisites on the online machine:
  - pnpm (matching packageManager in package.json)
  - uv
  - Node.js >= 24
  - Python >= 3.11

The bundle includes:
  - node_modules/ (fully resolved, with all postinstall artifacts)
  - uv cache (all Python wheels)
  - electron-builder cache (app-builder and related tools)
  - Verification that all vendored assets are present

On the air-gapped machine:
  bash scripts/install-offline.sh
  MESHCHATX_OFFLINE_BUILD=1 make build
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

WARM_PACKAGING="0"
OUT_DIR="${ROOT_DIR}/vendor/offline"

    while [[ $# -gt 0 ]]; do
    case "$1" in
        --warm-packaging)
            WARM_PACKAGING="1"
            shift
            ;;
        --out-dir)
            OUT_DIR="${2:?missing value for --out-dir}"
            shift 2
            ;;
        --)
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

require_cmd node
require_cmd pnpm
require_cmd uv
require_cmd python3

VERSION=$(node -p "require('./package.json').version")
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
BUNDLE_NAME="meshchatx-offline-bundle-${VERSION}-${PLATFORM}-${ARCH}"
BUNDLE_DIR="${OUT_DIR}/${BUNDLE_NAME}"

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}"

echo "==> [1/7] Verifying lockfiles..."
if [[ ! -f "pnpm-lock.yaml" ]]; then
    echo "Missing pnpm-lock.yaml. Run 'pnpm install' first." >&2
    exit 1
fi
if [[ ! -f "uv.lock" ]]; then
    echo "Missing uv.lock. Run 'uv lock' first." >&2
    exit 1
fi

echo "==> [2/7] Ensuring vendored assets..."
node scripts/fetch-micron-wasm.mjs
python3 scripts/build/fetch_reticulum_manual.py
python3 scripts/build/fetch_repository_wheels.py

echo "==> [3/7] Installing Node.js dependencies..."
pnpm install --frozen-lockfile

echo "==> [4/7] Running postinstall hooks..."
mkdir -p "${BUNDLE_DIR}/electron-builder-cache"
ELECTRON_BUILDER_CACHE="${BUNDLE_DIR}/electron-builder-cache" pnpm run electron-postinstall

echo "==> [5/7] Bundling node_modules..."
if tar --help 2>/dev/null | grep -q -- '--hard-dereference'; then
    tar czf "${BUNDLE_DIR}/node_modules.tar.gz" --hard-dereference node_modules/
else
    NM_BUNDLE="${BUNDLE_DIR}/node_modules-bundle"
    cp -rL node_modules "${NM_BUNDLE}"
    (cd "${BUNDLE_DIR}" && tar czf node_modules.tar.gz node_modules-bundle/)
    rm -rf "${NM_BUNDLE}"
fi

echo "==> [6/7] Installing Python dependencies and populating uv cache..."
mkdir -p "${BUNDLE_DIR}/uv-cache"
UV_CACHE_DIR="${BUNDLE_DIR}/uv-cache" uv sync --group dev

echo "==> [7/7] Finalizing..."
if [[ "${WARM_PACKAGING}" == "1" ]]; then
    echo "    Pre-downloading electron-builder packaging tools..."
    ELECTRON_BUILDER_CACHE="${BUNDLE_DIR}/electron-builder-cache" \
        npx electron-builder --linux dir --publish=never >/dev/null 2>&1 || true
fi

cat > "${BUNDLE_DIR}/.bundle-manifest.json" <<EOF
{
  "name": "meshchatx-offline-bundle",
  "version": "${VERSION}",
  "platform": "${PLATFORM}",
  "arch": "${ARCH}",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "warm_packaging": ${WARM_PACKAGING}
}
EOF

echo ""
echo "Offline bundle created: ${BUNDLE_DIR}"
echo ""
ls -lh "${BUNDLE_DIR}"
echo ""
echo "To transfer to an air-gapped machine:"
echo "  tar czf meshchatx-offline-${PLATFORM}-${ARCH}.tar.gz -C ${OUT_DIR} ${BUNDLE_NAME}"
echo ""
echo "On the air-gapped machine:"
echo "  tar xzf meshchatx-offline-${PLATFORM}-${ARCH}.tar.gz"
echo "  bash scripts/install-offline.sh"
echo "  MESHCHATX_OFFLINE_BUILD=1 make build"
