#!/bin/sh
# Install go-task from GitHub releases with SHA256 verification.
# Source: https://github.com/go-task/task
# Usage: setup-task.sh [version]
set -eu

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

echo "Installing Task v${TASK_VERSION} (${ARCH})"
curl -fsSL "${BASE_URL}/task_checksums.txt" -o /tmp/task-checksums.txt
curl -fsSL "${BASE_URL}/${TARBALL}" -o /tmp/task.tar.gz

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
