#!/bin/sh
# Install nuclei for CI DAST scanning.
# Downloads the pinned release zip and verifies it against the
# release checksums.txt before installing.
set -eu

NUCLEI_VERSION="${NUCLEI_VERSION:-3.11.1}"
RELEASE_BASE="https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}"

arch="$(uname -m)"
case "$arch" in
    x86_64|amd64) asset_arch=amd64 ;;
    aarch64|arm64) asset_arch=arm64 ;;
    *)
        echo "setup-nuclei.sh: unsupported uname -m: ${arch}" >&2
        exit 1
        ;;
esac

ASSET="nuclei_${NUCLEI_VERSION}_linux_${asset_arch}.zip"

curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/nuclei_checksums.txt \
    "${RELEASE_BASE}/nuclei_${NUCLEI_VERSION}_checksums.txt"
EXPECTED_SHA="$(awk -v f="${ASSET}" '$2 == f { print $1; exit }' ${TMPDIR:-/tmp}/nuclei_checksums.txt)"
if [ -z "${EXPECTED_SHA}" ]; then
    echo "setup-nuclei.sh: no SHA256 line for ${ASSET} in checksums.txt" >&2
    exit 1
fi

curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/nuclei.zip "${RELEASE_BASE}/${ASSET}"
echo "${EXPECTED_SHA}  ${TMPDIR:-/tmp}/nuclei.zip" | sha256sum -c

mkdir -p ${TMPDIR:-/tmp}/nuclei-bin
unzip -o ${TMPDIR:-/tmp}/nuclei.zip nuclei -d ${TMPDIR:-/tmp}/nuclei-bin
sh scripts/ci/exec-priv.sh install -m 0755 ${TMPDIR:-/tmp}/nuclei-bin/nuclei /usr/local/bin/nuclei
nuclei -version
