#!/bin/sh
# Install go-task from GitHub releases with SHA256 verification.
# Source: https://github.com/go-task/task
# Usage: setup-task.sh [version]
set -eu

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

TASK_VERSION="${1:-3.54.0}"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS" in
    linux)                OS_NAME="linux" ;;
    darwin)               OS_NAME="darwin" ;;
    msys*|mingw*|cygwin*) OS_NAME="windows" ;;
    *)                    echo "Unsupported OS: $OS" >&2; exit 1 ;;
esac

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64)   ARCH="amd64" ;;
    aarch64|arm64)  ARCH="arm64" ;;
    *)              echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

BASE_URL="https://github.com/go-task/task/releases/download/v${TASK_VERSION}"
case "$OS_NAME" in
    windows) TARBALL="task_windows_${ARCH}.zip" ;;
    *)       TARBALL="task_${OS_NAME}_${ARCH}.tar.gz" ;;
esac

# GitHub release CDN over HTTP/2 can drop the stream (curl 56, "tried 5 times").
# Default curl --retry skips that recv error. HTTP/1.1 plus --retry-all-errors
# recovers from 503 and dropped connections. GITHUB_TOKEN / GH_TOKEN avoids
# unauthenticated github.com rate limits. -L strips Authorization on the
# objects.githubusercontent.com redirect.
download_release() {
    dest="$1"
    url="$2"
    token="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
    if [ -n "$token" ]; then
        curl -fsSL --http1.1 \
            --retry 8 \
            --retry-all-errors \
            --retry-delay 4 \
            --retry-max-time 180 \
            --connect-timeout 20 \
            --max-time 180 \
            -H "Authorization: Bearer ${token}" \
            -o "$dest" \
            "$url"
    else
        curl -fsSL --http1.1 \
            --retry 8 \
            --retry-all-errors \
            --retry-delay 4 \
            --retry-max-time 180 \
            --connect-timeout 20 \
            --max-time 180 \
            -o "$dest" \
            "$url"
    fi
}

echo "Installing Task v${TASK_VERSION} (${ARCH})"
download_release ${TMPDIR:-/tmp}/task-checksums.txt "${BASE_URL}/task_checksums.txt"
download_release ${TMPDIR:-/tmp}/task.tar.gz "${BASE_URL}/${TARBALL}"

EXPECTED="$(grep "  ${TARBALL}\$" ${TMPDIR:-/tmp}/task-checksums.txt | cut -d' ' -f1)"
ACTUAL="$(cd "${TMPDIR:-/tmp}" && sha256sum task.tar.gz | cut -d' ' -f1)"
if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "SHA256 verification failed for ${TARBALL}" >&2
    echo "  expected: ${EXPECTED}" >&2
    echo "  got:      ${ACTUAL}" >&2
    rm -f ${TMPDIR:-/tmp}/task.tar.gz ${TMPDIR:-/tmp}/task-checksums.txt
    exit 1
fi
echo "SHA256 verified: ${ACTUAL}"

# /usr/local/bin is not writable on all self-hosted runners (and sudo may be
# unavailable). Fall back to a per-job writable dir exported via GITHUB_PATH.
extract_task() {
    _dest="$1"
    case "${TARBALL}" in
        *.zip) unzip -q -o "${TMPDIR:-/tmp}/task.tar.gz" -d "${_dest}" ;;
        *)     tar -xzf "${TMPDIR:-/tmp}/task.tar.gz" -C "${_dest}" task ;;
    esac
}
TASK_DEST="/usr/local/bin"
if [ ! -d "${TASK_DEST}" ] || { [ ! -w "${TASK_DEST}" ] && [ "$(id -u)" -ne 0 ] && ! sudo -n true 2>/dev/null; }; then
    # TMPDIR is normalized to a POSIX path by priv.sh (Git Bash reports
    # RUNNER_TEMP as D:\a\_temp, which does not belong on PATH).
    TASK_DEST="${TMPDIR:-${RUNNER_TEMP:-${HOME}/.local}}/bin"
    mkdir -p "${TASK_DEST}"
    extract_task "${TASK_DEST}"
    if [ -n "${GITHUB_PATH:-}" ]; then
        echo "${TASK_DEST}" >> "${GITHUB_PATH}"
    fi
    export PATH="${TASK_DEST}:${PATH}"
else
    case "${TARBALL}" in
        *.zip) run_priv unzip -q -o "${TMPDIR:-/tmp}/task.tar.gz" -d /usr/local/bin ;;
        *)     run_priv tar -xzf "${TMPDIR:-/tmp}/task.tar.gz" -C /usr/local/bin task ;;
    esac
fi
rm -f ${TMPDIR:-/tmp}/task.tar.gz ${TMPDIR:-/tmp}/task-checksums.txt

task --version
