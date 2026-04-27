#!/bin/sh
# Create SLSA v1 cosign bundle attestations next to each release binary under DIR.
# Requires: cosign on PATH; COSIGN_KEY_PATH to cosign private key PEM; COSIGN_PASSWORD
# if the key is encrypted. Run from repository root so scripts/ci/slsa-predicate.py resolves.
# Cosign v3+: uses cosign-signing-config-no-rekor.json (no Rekor upload); verify with
# cosign verify-blob-attestation --insecure-ignore-tlog=true when using the repo public key.
#
# Usage: attest-release-assets.sh <directory>
set -eu

DIR="${1:?directory}"
KEY="${COSIGN_KEY_PATH:?set COSIGN_KEY_PATH}"
SCI_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
SIGNCFG="${SCI_DIR}/cosign-signing-config-no-rekor.json"

if [ ! -f "$KEY" ]; then
    echo "attest-release-assets.sh: missing key file $KEY" >&2
    exit 1
fi
if [ ! -f "$SIGNCFG" ]; then
    echo "attest-release-assets.sh: missing signing config $SIGNCFG" >&2
    exit 1
fi

PRED="$(mktemp "${TMPDIR:-/tmp}/slsa-pred.XXXXXX")"
trap 'rm -f "$PRED"' EXIT INT

python3 scripts/ci/slsa-predicate.py > "$PRED"

find "$DIR" -type f ! -name '*.cosign.bundle' ! -name '*.sha256' ! -name '*.intoto.jsonl' | while IFS= read -r f; do
    case "$f" in
        */.git/*) continue ;;
    esac
    echo "attest: $f"
    cosign attest-blob --yes \
        --key "$KEY" \
        --signing-config "$SIGNCFG" \
        --predicate "$PRED" \
        --type slsaprovenance1 \
        --bundle "${f}.cosign.bundle" \
        "$f" >/dev/null
done

echo "attest-release-assets.sh: done"
