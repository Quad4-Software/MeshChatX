#!/usr/bin/env bash
# Install Node.js from nodejs.org official tarball with SHASUMS256 verification.
# Env: NODE_VERSION (default 24.11.1), NODE_INSTALL_DIR (default /usr/local).
set -euo pipefail

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

NODE_VERSION="${NODE_VERSION:-24.11.1}"
NODE_VERSION="${NODE_VERSION#v}"
NODE_INSTALL_DIR="${NODE_INSTALL_DIR:-/usr/local}"

ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64) NODE_ARCH="x64" ;;
    aarch64|arm64) NODE_ARCH="arm64" ;;
    *)
        echo "Unsupported architecture: ${ARCH}" >&2
        exit 1
        ;;
esac

BASE_URL="https://nodejs.org/dist/v${NODE_VERSION}"
TARBALL="node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz"
TMPDIR_NODE="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_NODE}"' EXIT

echo "Installing Node.js v${NODE_VERSION} (${NODE_ARCH})"
curl -fsSL --retry 8 --retry-all-errors --retry-delay 4 \
    --connect-timeout 20 --max-time 180 \
    -o "${TMPDIR_NODE}/${TARBALL}" "${BASE_URL}/${TARBALL}"
curl -fsSL --retry 8 --retry-all-errors --retry-delay 4 \
    --connect-timeout 20 --max-time 180 \
    -o "${TMPDIR_NODE}/SHASUMS256.txt" "${BASE_URL}/SHASUMS256.txt"

EXPECTED="$(grep "  ${TARBALL}\$" "${TMPDIR_NODE}/SHASUMS256.txt" | awk '{print $1}')"
ACTUAL="$(sha256sum "${TMPDIR_NODE}/${TARBALL}" | awk '{print $1}')"
if [ -z "${EXPECTED}" ] || [ "${EXPECTED}" != "${ACTUAL}" ]; then
    echo "SHA256 verification failed for ${TARBALL}" >&2
    echo "  expected: ${EXPECTED}" >&2
    echo "  got:      ${ACTUAL}" >&2
    exit 1
fi
echo "SHA256 verified: ${ACTUAL}"

tar -xJf "${TMPDIR_NODE}/${TARBALL}" -C "${TMPDIR_NODE}"
run_priv cp -a "${TMPDIR_NODE}/node-v${NODE_VERSION}-linux-${NODE_ARCH}/." "${NODE_INSTALL_DIR}/"

node --version
npm --version
