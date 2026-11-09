#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Install TinyGo so `tinygo` lands on PATH for WASM builds.
# Usage: sh scripts/ci/setup-tinygo.sh <version>  (e.g. 0.44.0)

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

VERSION="${1:?tinygo version required}"
TARBALL="tinygo${VERSION}.linux-amd64.tar.gz"
URL="https://github.com/tinygo-org/tinygo/releases/download/v${VERSION}/${TARBALL}"

if command -v tinygo >/dev/null 2>&1 && tinygo version | grep -q "${VERSION}"; then
    echo "tinygo ${VERSION} already installed"
    exit 0
fi

curl -fsSL -o "${TMPDIR:-/tmp}/${TARBALL}" "${URL}"

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
${TAR} -C "${DEST}" -xzf "${TMPDIR:-/tmp}/${TARBALL}"

BINDIR="${DEST}/tinygo/bin"
if [ -n "${GITHUB_PATH:-}" ]; then
    echo "${BINDIR}" >> "${GITHUB_PATH}"
fi

"${BINDIR}/tinygo" version
