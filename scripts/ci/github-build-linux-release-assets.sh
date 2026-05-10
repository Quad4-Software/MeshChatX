#!/usr/bin/env bash
# Build wheel, Linux AppImage/deb (x64 + arm64), optional RPM, frontend zip, and SBOM under ./release-assets/.
# Expects repo root as cwd, dependencies installed (task install / pnpm), and meshchatx/public populated when building Electron.
# Optional: SKIP_WHEEL=1, SKIP_ELECTRON=1, TRIVY_SBOM=0
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/ci-node-path.sh
. "$(dirname "$0")/ci-node-path.sh"

mkdir -p release-assets

HOST_ARCH="$(uname -m)"
case "$HOST_ARCH" in
    x86_64) NATIVE_ARCH="x64" ;;
    aarch64|arm64) NATIVE_ARCH="arm64" ;;
    *) NATIVE_ARCH="$HOST_ARCH" ;;
esac

if [ "${SKIP_WHEEL:-0}" != 1 ]; then
    if [ "$NATIVE_ARCH" = "x64" ]; then
        echo "Building Python wheel..."
        task build:wheel
    else
        echo "Skipping wheel on $NATIVE_ARCH runner (pure-Python wheel built on x64)."
    fi
else
    echo "Skipping wheel (SKIP_WHEEL=1)."
fi

if [ "${SKIP_ELECTRON:-0}" != 1 ]; then
    if [ "$NATIVE_ARCH" = "x64" ]; then
        echo "Electron linux x64..."
        pnpm run dist:linux-x64
    elif [ "$NATIVE_ARCH" = "arm64" ]; then
        echo "Electron linux arm64..."
        pnpm run dist:linux-arm64
    fi

    if [ "$NATIVE_ARCH" = "x64" ]; then
        echo "RPM (best-effort)..."
        if ! task dist:fe:rpm; then
            echo "RPM build failed or skipped; continuing." >&2
        fi
    fi
else
    echo "Skipping Electron packages (SKIP_ELECTRON=1)."
fi

echo "Collecting release files..."
find dist -maxdepth 1 -type f \( -name "*-linux*.AppImage" -o -name "*-linux*.deb" -o -name "*-linux*.rpm" \) -exec cp -f {} release-assets/ \; 2>/dev/null || true
find python-dist -maxdepth 1 -type f -name "*.whl" -exec cp -f {} release-assets/ \; 2>/dev/null || true

if [ -d meshchatx/public ] && [ "${SKIP_ELECTRON:-0}" != 1 ]; then
    ( cd meshchatx/public && zip -qr "${ROOT}/release-assets/meshchatx-frontend.zip" . )
fi

{
    echo "## Integrity"
    echo ""
    echo "Each artifact may have a matching **\`*.cosign.bundle\`** when repository signing secrets are configured (see SECURITY.md)."
    echo ""
    echo "SBOM: **\`sbom.cyclonedx.json\`** (CycloneDX) when produced by CI."
} > release-body.md

if [ "${TRIVY_SBOM:-1}" != 0 ] && command -v trivy >/dev/null 2>&1; then
    echo "Generating SBOM..."
    trivy fs --format cyclonedx --include-dev-deps --output release-assets/sbom.cyclonedx.json .
else
    echo "Skipping SBOM (trivy not on PATH or TRIVY_SBOM=0)." >&2
fi

echo "github-build-linux-release-assets.sh: done; see ./release-assets/"
