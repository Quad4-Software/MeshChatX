#!/bin/sh
# Install Node.js from the official binary distribution with SHA256 verification.
# Source: https://nodejs.org
# Usage: setup-node.sh [major_version]
set -eu

. "$(dirname "$0")/priv.sh"

NODE_MAJOR="${1:-24}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="x64" ;;
    aarch64) ARCH="arm64" ;;
    armv7l)  ARCH="armv7l" ;;
    *)       echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

DIST_URL="https://nodejs.org/dist/latest-v${NODE_MAJOR}.x"

curl -fsSL "${DIST_URL}/SHASUMS256.txt" -o /tmp/node-shasums.txt

VERSION="$(grep -o "node-v[0-9.]*-linux-${ARCH}" /tmp/node-shasums.txt \
    | head -1 \
    | sed "s/-linux-${ARCH}//" \
    | sed 's/node-//')"

if [ -z "$VERSION" ]; then
    echo "Failed to resolve Node.js v${NODE_MAJOR} for ${ARCH}" >&2
    exit 1
fi

TARBALL="node-${VERSION}-linux-${ARCH}.tar.xz"
echo "Installing Node.js ${VERSION} (${ARCH})"
curl -fsSL "${DIST_URL}/${TARBALL}" -o /tmp/node.tar.xz

EXPECTED="$(grep " ${TARBALL}\$" /tmp/node-shasums.txt | cut -d' ' -f1)"
ACTUAL="$(sha256sum /tmp/node.tar.xz | cut -d' ' -f1)"
if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "SHA256 verification failed for ${TARBALL}" >&2
    echo "  expected: ${EXPECTED}" >&2
    echo "  got:      ${ACTUAL}" >&2
    rm -f /tmp/node.tar.xz /tmp/node-shasums.txt
    exit 1
fi
echo "SHA256 verified: ${ACTUAL}"

run_priv tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1
rm -f /tmp/node.tar.xz /tmp/node-shasums.txt

export PATH="/usr/local/bin:$PATH"

# Act / Gitea runners often ship an older Node in /usr/bin; later steps start a new shell.
if [ -n "${GITHUB_ENV:-}" ]; then
    echo "PATH=/usr/local/bin:$PATH" >> "$GITHUB_ENV"
fi
if [ -n "${GITEA_ENV:-}" ]; then
    echo "PATH=/usr/local/bin:$PATH" >> "$GITEA_ENV"
fi
if [ -n "${GITHUB_PATH:-}" ]; then
    echo "/usr/local/bin" >> "$GITHUB_PATH"
fi
if [ -n "${GITEA_PATH:-}" ]; then
    echo "/usr/local/bin" >> "$GITEA_PATH"
fi

node --version
npm --version
