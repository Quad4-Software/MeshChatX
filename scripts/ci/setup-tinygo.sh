#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Install TinyGo into /usr/local so `tinygo` lands on PATH for WASM builds.
# Usage: sh scripts/ci/setup-tinygo.sh <version>  (e.g. 0.42.0)

set -eu

VERSION="${1:?tinygo version required}"
TARBALL="tinygo${VERSION}.linux-amd64.tar.gz"
URL="https://github.com/tinygo-org/tinygo/releases/download/v${VERSION}/${TARBALL}"

if command -v tinygo >/dev/null 2>&1 && tinygo version | grep -q "${VERSION}"; then
    echo "tinygo ${VERSION} already installed"
    exit 0
fi

curl -fsSL -o "/tmp/${TARBALL}" "${URL}"
tar -C /usr/local -xzf "/tmp/${TARBALL}"

if [ -n "${GITHUB_PATH:-}" ]; then
    echo "/usr/local/tinygo/bin" >> "${GITHUB_PATH}"
fi

/usr/local/tinygo/bin/tinygo version
