#!/usr/bin/env bash
# Host helper: build MeshChatX Windows Electron artifacts with Dockerfile.electron-wine.
# Optional path. GitHub Actions windows-latest remains the release default.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

IMAGE="${MESHCHATX_ELECTRON_WINE_IMAGE:-meshchatx-electron-wine:local}"
FILE="${MESHCHATX_ELECTRON_WINE_DOCKERFILE:-docker/Dockerfile.electron-wine}"
TARGETS="${MESHCHATX_ELECTRON_WINE_TARGETS:-win}"
OUT_DIR="${MESHCHATX_ELECTRON_WINE_OUT:-./meshchatx-artifacts-win}"
BASE_IMAGE="${ELECTRON_BUILDER_IMAGE:-electronuserland/builder:24-wine-05.26}"

echo "Building ${IMAGE} (targets=${TARGETS}, base=${BASE_IMAGE})..."
docker build \
    -f "$FILE" \
    --build-arg "MESHCHATX_ELECTRON_WINE_TARGETS=${TARGETS}" \
    --build-arg "ELECTRON_BUILDER_IMAGE=${BASE_IMAGE}" \
    -t "$IMAGE" \
    .

cid="$(docker create "$IMAGE")"
cleanup() {
    docker rm -f "$cid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
docker cp "${cid}:/artifacts/." "$OUT_DIR/"
echo "Artifacts copied to ${OUT_DIR}"
ls -la "$OUT_DIR" | head -40 || true
