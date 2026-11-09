#!/bin/sh
# Install grype for CI SBOM re-scanning.
# Downloads the pinned release tarball and verifies it against the
# release checksums.txt before installing.
set -eu

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

GRYPE_VERSION="${GRYPE_VERSION:-0.119.0}"
RELEASE_BASE="https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}"

arch="$(uname -m)"
case "$arch" in
    x86_64|amd64) asset_arch=amd64 ;;
    aarch64|arm64) asset_arch=arm64 ;;
    *)
        echo "setup-grype.sh: unsupported uname -m: ${arch}" >&2
        exit 1
        ;;
esac

ASSET="grype_${GRYPE_VERSION}_linux_${asset_arch}.tar.gz"

curl -fsSL --http1.1 --retry 8 --retry-all-errors --retry-delay 4 --retry-max-time 240 --connect-timeout 20 --max-time 300 -o ${TMPDIR:-/tmp}/grype_checksums.txt \
    "${RELEASE_BASE}/grype_${GRYPE_VERSION}_checksums.txt"
EXPECTED_SHA="$(awk -v f="${ASSET}" '$2 == f { print $1; exit }' ${TMPDIR:-/tmp}/grype_checksums.txt)"
if [ -z "${EXPECTED_SHA}" ]; then
    echo "setup-grype.sh: no SHA256 line for ${ASSET} in checksums.txt" >&2
    exit 1
fi

curl -fsSL --http1.1 --retry 8 --retry-all-errors --retry-delay 4 --retry-max-time 240 --connect-timeout 20 --max-time 300 -o ${TMPDIR:-/tmp}/grype.tar.gz "${RELEASE_BASE}/${ASSET}"
echo "${EXPECTED_SHA}  ${TMPDIR:-/tmp}/grype.tar.gz" | sha256sum -c

mkdir -p ${TMPDIR:-/tmp}/grype-bin
tar -xzf ${TMPDIR:-/tmp}/grype.tar.gz -C ${TMPDIR:-/tmp}/grype-bin grype
install_tool ${TMPDIR:-/tmp}/grype-bin/grype grype
grype version
