#!/bin/sh
# Create SLSA v1 cosign bundle attestations next to each release binary under DIR.
# Requires: cosign on PATH, COSIGN_KEY_PATH to cosign private key PEM, and COSIGN_PASSWORD
# if the key is encrypted. Run from repository root so scripts/ci/slsa-predicate.py resolves.
# Cosign v3+: uses cosign-signing-config-no-rekor.json (no Rekor upload). Verify with
# cosign verify-blob-attestation --insecure-ignore-tlog=true when using the repo public key.
#
# Usage: attest-release-assets.sh <directory>
set -eu

# /tmp can disappear mid-run on self-hosted runners (tmpfiles cleanup,
# unmounted tmpfs), so never depend on it: mktemp and friends honour
# TMPDIR. Always point TMPDIR at a user-writable per-job dir and
# propagate it to later steps via GITHUB_ENV.
_ci_tmp=""
for _ci_cand in "${RUNNER_TEMP:-}" "${HOME:-}" "${GITHUB_WORKSPACE:-}"; do
    [ -n "${_ci_cand}" ] || continue
    _ci_cand="${_ci_cand}/.meshchatx-ci-tmp"
    if mkdir -p "${_ci_cand}" 2>/dev/null && [ -w "${_ci_cand}" ]; then
        _ci_tmp="${_ci_cand}"
        break
    fi
done
if [ -n "${_ci_tmp}" ]; then
    TMPDIR="${_ci_tmp}"
    export TMPDIR
    [ -n "${GITHUB_ENV:-}" ] && echo "TMPDIR=${TMPDIR}" >> "${GITHUB_ENV}"
    echo "ci: TMPDIR=${TMPDIR}"
else
    echo "ci: WARNING: no writable temp dir available" >&2
fi
unset _ci_cand
unset _ci_tmp


DIR="${1:?directory}"
KEY="${COSIGN_KEY_PATH:?set COSIGN_KEY_PATH}"
SCI_DIR="$(CDPATH='' cd -- "$(dirname "$0")" && pwd)"
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

find "$DIR" -type f ! -name '*.cosign.bundle' ! -name '*.sha256' ! -name '*.intoto.jsonl' \
    ! -name 'builder-debug.yml' \
    ! -name 'library.zip' \
    ! -name '*.so.yml' \
    ! -path '*/win-unpacked/*' \
    ! -path '*/linux-unpacked/*' \
    ! -path '*/mac-universal/*' \
    ! -path '*/mac-arm64/*' \
    ! -path '*/mac-x64/*' \
    ! -path '*/mac/*.app/*' \
    ! -path '*/mac/*.app' \
    | while IFS= read -r f; do
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
