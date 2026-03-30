#!/bin/sh
# Verify a cosign SLSA bundle for a release binary using the repository public key.
# Checks Sigstore Rekor (public log) unless COSIGN_REKOR_URL points elsewhere.
# Usage: verify-release-attestation.sh <blob-file> <bundle-file>
# Env: COSIGN_PUBLIC_KEY (default cosign.pub)
set -eu

BLOB="${1:?blob path}"
BUNDLE="${2:?bundle path}"
PUB="${COSIGN_PUBLIC_KEY:-cosign.pub}"

if [ ! -f "$PUB" ]; then
    echo "Missing $PUB (generate a key pair with cosign and commit the .pub file)" >&2
    exit 1
fi

exec cosign verify-blob-attestation \
    --key "$PUB" \
    --bundle "$BUNDLE" \
    --type slsaprovenance1 \
    "$BLOB"
