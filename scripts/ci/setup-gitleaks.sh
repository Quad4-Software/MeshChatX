#!/bin/sh
# Install gitleaks for CI secret scanning.
#
# Downloads the release tarball plus upstream checksums.txt, verifies the
# tarball sha256, and installs the binary to /usr/local/bin.
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GITLEAKS_VERSION="${GITLEAKS_VERSION:-8.28.0}"
GITLEAKS_RELEASE_BASE="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}"
ASSET="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"

cd /tmp
curl -fsSL --retry 5 --retry-delay 2 -o gitleaks_checksums.txt "${GITLEAKS_RELEASE_BASE}/checksums.txt"
curl -fsSL --retry 5 --retry-delay 2 -o gitleaks.tar.gz "${GITLEAKS_RELEASE_BASE}/${ASSET}"

EXPECTED_SHA="$(awk -v f="${ASSET}" '$2 == f { print $1; exit }' gitleaks_checksums.txt)"
if [ -z "${EXPECTED_SHA}" ]; then
    echo "setup-gitleaks.sh: no SHA256 line for ${ASSET} in checksums.txt" >&2
    exit 1
fi
echo "${EXPECTED_SHA}  gitleaks.tar.gz" | sha256sum -c

tar -xzf gitleaks.tar.gz gitleaks
sh "${REPO_ROOT}/scripts/ci/exec-priv.sh" install -m 0755 /tmp/gitleaks /usr/local/bin/gitleaks
gitleaks version
