#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Install TinyGo so `tinygo` lands on PATH for WASM builds.
# Usage: sh scripts/ci/setup-tinygo.sh <version>  (e.g. 0.44.0)

set -eu

VERSION="${1:?tinygo version required}"
TARBALL="tinygo${VERSION}.linux-amd64.tar.gz"
URL="https://github.com/tinygo-org/tinygo/releases/download/v${VERSION}/${TARBALL}"

if command -v tinygo >/dev/null 2>&1 && tinygo version | grep -q "${VERSION}"; then
    echo "tinygo ${VERSION} already installed"
    exit 0
fi

curl -fsSL -o "/tmp/${TARBALL}" "${URL}"

# /usr/local is not writable on all self-hosted runners (and sudo may be
# unavailable under no_new_privs). Fall back to a per-user dir on PATH.
DEST="/usr/local"
TAR="tar"
if [ ! -w /usr/local ]; then
    if sudo -n true 2>/dev/null; then
        TAR="sudo tar"
    else
        DEST="${HOME}/.local/meshchatx-ci"
        mkdir -p "${DEST}"
    fi
fi
${TAR} -C "${DEST}" -xzf "/tmp/${TARBALL}"

BINDIR="${DEST}/tinygo/bin"
if [ -n "${GITHUB_PATH:-}" ]; then
    echo "${BINDIR}" >> "${GITHUB_PATH}"
fi

"${BINDIR}/tinygo" version
