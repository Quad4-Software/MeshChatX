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

# Resolve the install destination first so an existing copy (from an
# earlier job on a persistent self-hosted runner) is reused instead of
# re-downloading the tarball every run.
DEST="/usr/local"
if [ ! -w /usr/local ]; then
    if sudo -n true 2>/dev/null; then
        :
    else
        DEST="${HOME}/.local/meshchatx-ci"
    fi
fi
BINDIR="${DEST}/tinygo/bin"

_existing=""
for _cand in "$(command -v tinygo 2>/dev/null || true)" \
    "/usr/local/tinygo/bin/tinygo" \
    "${HOME}/.local/meshchatx-ci/tinygo/bin/tinygo" \
    "${HOME}/.local/bin/tinygo"; do
    [ -n "${_cand}" ] && [ -x "${_cand}" ] || continue
    if "${_cand}" version 2>/dev/null | grep -q "${VERSION}"; then
        _existing="${_cand}"
        break
    fi
done
unset _cand

if [ -n "${_existing}" ]; then
    echo "tinygo ${VERSION} already installed at ${_existing}"
    if [ -n "${GITHUB_PATH:-}" ]; then
        echo "$(dirname "${_existing}")" >> "${GITHUB_PATH}"
    fi
    exit 0
fi

# GitHub release downloads intermittently return 5xx for minutes at a
# time, so retry both inside curl and across a few spaced attempts.
_attempt=0
while [ "${_attempt}" -lt 3 ]; do
    _attempt=$((_attempt + 1))
    if curl -fsSL --http1.1 \
        --retry 8 \
        --retry-all-errors \
        --retry-delay 4 \
        --retry-max-time 240 \
        --connect-timeout 20 \
        --max-time 300 \
        -o "${TMPDIR:-/tmp}/${TARBALL}" "${URL}"; then
        break
    fi
    if [ "${_attempt}" -ge 3 ]; then
        echo "tinygo download failed after ${_attempt} attempts" >&2
        exit 1
    fi
    echo "tinygo download attempt ${_attempt} failed; retrying in 30s" >&2
    sleep 30
done
unset _attempt

# /usr/local is not writable on all self-hosted runners (and sudo may be
# unavailable under no_new_privs). DEST was resolved above.
TAR="tar"
if [ "${DEST}" = "/usr/local" ] && [ ! -w /usr/local ]; then
    TAR="sudo tar"
fi
mkdir -p "${DEST}"
${TAR} -C "${DEST}" -xzf "${TMPDIR:-/tmp}/${TARBALL}"

if [ -n "${GITHUB_PATH:-}" ]; then
    echo "${BINDIR}" >> "${GITHUB_PATH}"
fi

"${BINDIR}/tinygo" version
