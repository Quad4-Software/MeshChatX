#!/bin/sh
# Install rekor-cli from GitHub releases with SHA256 verification.
# Usage: setup-rekor-cli.sh [version]
set -eu

. "$(dirname "$0")/priv.sh"

REKOR_VERSION="${1:-1.5.1}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)
        BINARY="rekor-cli-linux-amd64"
        EXPECTED_SHA256="0b4964af85477892c37039fb80793b151864970d19838873eaa1a777ca2fb813"
        ;;
    aarch64)
        BINARY="rekor-cli-linux-arm64"
        EXPECTED_SHA256="6417ea36bea9239125ec21e73c5d9b5e7e837b580cfdfea1e47e04bb02235534"
        ;;
    *)
        echo "Unsupported architecture: $ARCH" >&2
        exit 1
        ;;
esac

BASE_URL="https://github.com/sigstore/rekor/releases/download/v${REKOR_VERSION}"
curl -fsSL "${BASE_URL}/${BINARY}" -o /tmp/rekor-cli

ACTUAL="$(sha256sum /tmp/rekor-cli | awk '{print $1}')"
if [ "$EXPECTED_SHA256" != "$ACTUAL" ]; then
    echo "SHA256 verification failed for ${BINARY}" >&2
    rm -f /tmp/rekor-cli
    exit 1
fi

run_priv install -m 0755 /tmp/rekor-cli /usr/local/bin/rekor-cli
rm -f /tmp/rekor-cli
rekor-cli version
