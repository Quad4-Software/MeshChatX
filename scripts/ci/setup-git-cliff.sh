#!/bin/sh
# Install git-cliff for changelog generation in CI.
# Downloads the pinned release archive and verifies the .sha512 checksum.
set -eu

CLIFF_VERSION="${CLIFF_VERSION:-2.14.2}"
BASE="https://github.com/orhun/git-cliff/releases/download/v${CLIFF_VERSION}"

arch="$(uname -m)"
case "$arch" in
    x86_64|amd64) asset_arch=x86_64 ;;
    aarch64|arm64) asset_arch=aarch64 ;;
    *)
        echo "setup-git-cliff.sh: unsupported uname -m: ${arch}" >&2
        exit 1
        ;;
esac

ASSET="git-cliff-${CLIFF_VERSION}-${asset_arch}-unknown-linux-gnu.tar.gz"

curl -fsSL --retry 5 --retry-delay 2 -o "${TMPDIR:-/tmp}/git-cliff.sha512" \
    "${BASE}/${ASSET}.sha512"
curl -fsSL --retry 5 --retry-delay 2 -o "${TMPDIR:-/tmp}/${ASSET}" \
    "${BASE}/${ASSET}"
(cd "${TMPDIR:-/tmp}" && sha512sum -c git-cliff.sha512)

mkdir -p "${TMPDIR:-/tmp}/git-cliff-bin"
tar -xzf "${TMPDIR:-/tmp}/${ASSET}" -C "${TMPDIR:-/tmp}/git-cliff-bin" \
    --strip-components=1 "git-cliff-${CLIFF_VERSION}/git-cliff"
sh scripts/ci/exec-priv.sh install -m 0755 "${TMPDIR:-/tmp}/git-cliff-bin/git-cliff" /usr/local/bin/git-cliff
git-cliff --version
