#!/bin/sh
# Install helm for CI chart linting.
#
# Downloads the release tarball plus the upstream sha256 checksum, verifies
# the tarball, and installs the binary to /usr/local/bin.
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HELM_VERSION="${HELM_VERSION:-4.3.0}"
ASSET="helm-v${HELM_VERSION}-linux-amd64.tar.gz"
BASE_URL="https://get.helm.sh"

cd /tmp
curl -fsSL --retry 5 --retry-delay 2 -o helm_checksum.txt "${BASE_URL}/${ASSET}.sha256sum"
curl -fsSL --retry 5 --retry-delay 2 -o helm.tar.gz "${BASE_URL}/${ASSET}"

# The checksum file contains the bare digest for the tarball.
EXPECTED_SHA="$(awk '{ print $1; exit }' helm_checksum.txt)"
if [ -z "${EXPECTED_SHA}" ]; then
    echo "setup-helm.sh: empty checksum for ${ASSET}" >&2
    exit 1
fi
echo "${EXPECTED_SHA}  helm.tar.gz" | sha256sum -c

tar -xzf helm.tar.gz linux-amd64/helm
sh "${REPO_ROOT}/scripts/ci/exec-priv.sh" install -m 0755 /tmp/linux-amd64/helm /usr/local/bin/helm
helm version
