#!/usr/bin/env bash
# Pre-download the electron-builder AppImage toolset into ELECTRON_BUILDER_CACHE.
# GitHub release CDN over HTTP/2 (got inside electron-builder) often resets the
# TLS stream after freeze has already finished (read ECONNRESET). curl HTTP/1.1
# plus --retry-all-errors matches scripts/ci/setup-task.sh.
#
# Pins must match package.json build.toolsets.appimage and the sha256 in
# app-builder-lib toolsets/linux.js for that version (electron-builder 26.15.3:
# appimage@1.0.2).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

APPIMAGE_TOOLSET="1.0.2"
FILENAME="appimage-tools-runtime-20251108.tar.gz"
SHA256="a784a8c26331ec2e945c23d6bdb14af5c9df27f5939825d84b8709c61dc81eb0"
RELEASE_NAME="appimage@${APPIMAGE_TOOLSET}"
URL="https://github.com/electron-userland/electron-builder-binaries/releases/download/${RELEASE_NAME}/${FILENAME}"

pkg_toolset="$(node -p "require('./package.json').build.toolsets.appimage" 2>/dev/null || true)"
if [ "$pkg_toolset" != "$APPIMAGE_TOOLSET" ]; then
    echo "github-warm-appimage-tools.sh: package.json build.toolsets.appimage is '${pkg_toolset:-missing}', script pin is '${APPIMAGE_TOOLSET}'" >&2
    echo "Update APPIMAGE_TOOLSET, FILENAME, and SHA256 in this script to match app-builder-lib." >&2
    exit 1
fi

electron_builder_cache_dir() {
    if [ -n "${ELECTRON_BUILDER_CACHE:-}" ]; then
        case "${ELECTRON_BUILDER_CACHE}" in
            /*)
                printf '%s\n' "${ELECTRON_BUILDER_CACHE}"
                return
                ;;
        esac
    fi
    if [ -n "${XDG_CACHE_HOME:-}" ]; then
        case "${XDG_CACHE_HOME}" in
            /*)
                printf '%s\n' "${XDG_CACHE_HOME}/electron-builder"
                return
                ;;
        esac
    fi
    printf '%s\n' "${HOME}/.cache/electron-builder"
}

CACHE_DIR="$(electron_builder_cache_dir)"
DEST_DIR="${CACHE_DIR}/${RELEASE_NAME}"
DEST="${DEST_DIR}/${FILENAME}"
mkdir -p "$DEST_DIR"

hash_ok() {
    [ -f "$1" ] || return 1
    local actual
    actual="$(sha256sum "$1" | cut -d' ' -f1)"
    [ "$actual" = "$SHA256" ]
}

if hash_ok "$DEST"; then
    echo "github-warm-appimage-tools.sh: using cached ${DEST}"
    exit 0
fi

if [ "${MESHCHATX_OFFLINE_BUILD:-0}" = "1" ]; then
    echo "github-warm-appimage-tools.sh: MESHCHATX_OFFLINE_BUILD=1 but ${DEST} is missing or checksum-mismatched" >&2
    exit 1
fi

download_release() {
    dest="$1"
    url="$2"
    token="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
    if [ -n "$token" ]; then
        curl -fsSL --http1.1 \
            --retry 8 \
            --retry-all-errors \
            --retry-delay 4 \
            --retry-max-time 180 \
            --connect-timeout 20 \
            --max-time 180 \
            -H "Authorization: Bearer ${token}" \
            -o "$dest" \
            "$url"
    else
        curl -fsSL --http1.1 \
            --retry 8 \
            --retry-all-errors \
            --retry-delay 4 \
            --retry-max-time 180 \
            --connect-timeout 20 \
            --max-time 180 \
            -o "$dest" \
            "$url"
    fi
}

TMP="${DEST}.tmp"
rm -f "$TMP" "$DEST"
echo "github-warm-appimage-tools.sh: downloading ${FILENAME} (${RELEASE_NAME})"
download_release "$TMP" "$URL"

ACTUAL="$(sha256sum "$TMP" | cut -d' ' -f1)"
if [ "$ACTUAL" != "$SHA256" ]; then
    echo "github-warm-appimage-tools.sh: SHA256 mismatch for ${FILENAME}" >&2
    echo "  expected: ${SHA256}" >&2
    echo "  got:      ${ACTUAL}" >&2
    rm -f "$TMP"
    exit 1
fi

mv -f "$TMP" "$DEST"
echo "github-warm-appimage-tools.sh: cached ${DEST} (${ACTUAL})"
