#!/bin/sh
# Install cosign from GitHub releases with SHA256 verification.
# Usage: setup-cosign.sh [version]
set -eu

COSIGN_VERSION="${1:-3.0.5}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    *)       echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

BASE_URL="https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}"
BINARY="cosign-linux-${ARCH}"
CHECKSUMS_URL="${BASE_URL}/cosign_checksums.txt"

curl -fsSL "$CHECKSUMS_URL" -o /tmp/cosign-checksums.txt
curl -fsSL "${BASE_URL}/${BINARY}" -o /tmp/cosign

EXPECTED="$(grep "  ${BINARY}\$" /tmp/cosign-checksums.txt | awk '{print $1}')"
ACTUAL="$(sha256sum /tmp/cosign | awk '{print $1}')"
if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "SHA256 verification failed for ${BINARY}" >&2
    rm -f /tmp/cosign /tmp/cosign-checksums.txt
    exit 1
fi

sudo install -m 0755 /tmp/cosign /usr/local/bin/cosign
rm -f /tmp/cosign /tmp/cosign-checksums.txt
cosign version
