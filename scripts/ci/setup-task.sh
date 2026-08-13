#!/bin/sh
# Install go-task from GitHub releases with SHA256 verification.
# Source: https://github.com/go-task/task
# Usage: setup-task.sh [version]
set -eu

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

TASK_VERSION="${1:-3.49.1}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    *)       echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

BASE_URL="https://github.com/go-task/task/releases/download/v${TASK_VERSION}"
TARBALL="task_linux_${ARCH}.tar.gz"

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
download_release /tmp/task-checksums.txt "${BASE_URL}/task_checksums.txt"
download_release /tmp/task.tar.gz "${BASE_URL}/${TARBALL}"

EXPECTED="$(grep "  ${TARBALL}\$" /tmp/task-checksums.txt | cut -d' ' -f1)"
ACTUAL="$(sha256sum /tmp/task.tar.gz | cut -d' ' -f1)"
if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "SHA256 verification failed for ${TARBALL}" >&2
    echo "  expected: ${EXPECTED}" >&2
    echo "  got:      ${ACTUAL}" >&2
    rm -f /tmp/task.tar.gz /tmp/task-checksums.txt
    exit 1
fi
echo "SHA256 verified: ${ACTUAL}"

run_priv tar -xzf /tmp/task.tar.gz -C /usr/local/bin task
rm -f /tmp/task.tar.gz /tmp/task-checksums.txt

task --version
