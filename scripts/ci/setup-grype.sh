#!/bin/sh
# Install grype for CI SBOM re-scanning.
# Downloads the pinned release tarball and verifies it against the
# release checksums.txt before installing.
set -eu

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

curl -fsSL --retry 5 --retry-delay 2 -o /tmp/grype_checksums.txt \
    "${RELEASE_BASE}/grype_${GRYPE_VERSION}_checksums.txt"
EXPECTED_SHA="$(awk -v f="${ASSET}" '$2 == f { print $1; exit }' /tmp/grype_checksums.txt)"
if [ -z "${EXPECTED_SHA}" ]; then
    echo "setup-grype.sh: no SHA256 line for ${ASSET} in checksums.txt" >&2
    exit 1
fi

curl -fsSL --retry 5 --retry-delay 2 -o /tmp/grype.tar.gz "${RELEASE_BASE}/${ASSET}"
echo "${EXPECTED_SHA}  /tmp/grype.tar.gz" | sha256sum -c

mkdir -p /tmp/grype-bin
tar -xzf /tmp/grype.tar.gz -C /tmp/grype-bin grype
sh scripts/ci/exec-priv.sh install -m 0755 /tmp/grype-bin/grype /usr/local/bin/grype
grype version
