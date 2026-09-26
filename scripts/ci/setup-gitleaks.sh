#!/bin/sh
# Install gitleaks for CI secret scanning.
# Downloads the pinned release tarball and verifies it against the
# release checksums.txt before installing.
set -eu

GITLEAKS_VERSION="${GITLEAKS_VERSION:-8.30.1}"
RELEASE_BASE="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}"

arch="$(uname -m)"
case "$arch" in
    x86_64|amd64) asset_arch=linux_x64 ;;
    aarch64|arm64) asset_arch=linux_arm64 ;;
    *)
        echo "setup-gitleaks.sh: unsupported uname -m: ${arch}" >&2
        exit 1
        ;;
esac

ASSET="gitleaks_${GITLEAKS_VERSION}_${asset_arch}.tar.gz"

curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/gitleaks_checksums.txt \
    "${RELEASE_BASE}/gitleaks_${GITLEAKS_VERSION}_checksums.txt"
EXPECTED_SHA="$(awk -v f="${ASSET}" '$2 == f { print $1; exit }' ${TMPDIR:-/tmp}/gitleaks_checksums.txt)"
if [ -z "${EXPECTED_SHA}" ]; then
    echo "setup-gitleaks.sh: no SHA256 line for ${ASSET} in checksums.txt" >&2
    exit 1
fi

curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/gitleaks.tar.gz "${RELEASE_BASE}/${ASSET}"
echo "${EXPECTED_SHA}  ${TMPDIR:-/tmp}/gitleaks.tar.gz" | sha256sum -c

mkdir -p ${TMPDIR:-/tmp}/gitleaks-bin
tar -xzf ${TMPDIR:-/tmp}/gitleaks.tar.gz -C ${TMPDIR:-/tmp}/gitleaks-bin gitleaks
sh scripts/ci/exec-priv.sh install -m 0755 ${TMPDIR:-/tmp}/gitleaks-bin/gitleaks /usr/local/bin/gitleaks
gitleaks version
