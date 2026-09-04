#!/usr/bin/env bash
# Install UV from GitHub releases with SHA256 verification (no pip bootstrap).
# Set UV_VERSION to override the default. Optional UV_INSTALL_DIR (default /usr/local/bin).
set -euo pipefail

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

UV_VERSION="${UV_VERSION:-0.11.15}"
UV_INSTALL_DIR="${UV_INSTALL_DIR:-/usr/local/bin}"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "${OS}" in
    linux)
        case "${ARCH}" in
            x86_64) TARGET="x86_64-unknown-linux-gnu" ;;
            aarch64) TARGET="aarch64-unknown-linux-gnu" ;;
            *)
                echo "Unsupported Linux architecture: ${ARCH}" >&2
                exit 1
                ;;
        esac
        EXT="tar.gz"
        ;;
    darwin)
        case "${ARCH}" in
            x86_64) TARGET="x86_64-apple-darwin" ;;
            arm64) TARGET="aarch64-apple-darwin" ;;
            *)
                echo "Unsupported macOS architecture: ${ARCH}" >&2
                exit 1
                ;;
        esac
        EXT="tar.gz"
        ;;
    mingw*|msys*|cygwin*)
        case "${ARCH}" in
            x86_64|amd64) TARGET="x86_64-pc-windows-msvc" ;;
            aarch64|arm64) TARGET="aarch64-pc-windows-msvc" ;;
            *)
                echo "Unsupported Windows architecture: ${ARCH}" >&2
                exit 1
                ;;
        esac
        EXT="zip"
        ;;
    *)
        echo "Unsupported platform: ${OS}-${ARCH}" >&2
        exit 1
        ;;
esac

ASSET="uv-${TARGET}.${EXT}"
BASE_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}"
TMPDIR_UV="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_UV}"' EXIT

download() {
    dest="$1"
    url="$2"
    token="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
    if [ -n "${token}" ]; then
        curl -fsSL --http1.1 \
            --retry 8 \
            --retry-all-errors \
            --retry-delay 4 \
            --retry-max-time 180 \
            --connect-timeout 20 \
            --max-time 180 \
            -H "Authorization: Bearer ${token}" \
            -o "${dest}" \
            "${url}"
    else
        curl -fsSL --http1.1 \
            --retry 8 \
            --retry-all-errors \
            --retry-delay 4 \
            --retry-max-time 180 \
            --connect-timeout 20 \
            --max-time 180 \
            -o "${dest}" \
            "${url}"
    fi
}

echo "Installing uv ${UV_VERSION} (${TARGET})"
download "${TMPDIR_UV}/${ASSET}" "${BASE_URL}/${ASSET}"
download "${TMPDIR_UV}/${ASSET}.sha256" "${BASE_URL}/${ASSET}.sha256"

EXPECTED="$(awk '{print $1}' "${TMPDIR_UV}/${ASSET}.sha256")"
ACTUAL="$(sha256sum "${TMPDIR_UV}/${ASSET}" | awk '{print $1}')"
if [ -z "${EXPECTED}" ] || [ "${EXPECTED}" != "${ACTUAL}" ]; then
    echo "SHA256 verification failed for ${ASSET}" >&2
    echo "  expected: ${EXPECTED}" >&2
    echo "  got:      ${ACTUAL}" >&2
    exit 1
fi
echo "SHA256 verified: ${ACTUAL}"

install_bin() {
    src="$1"
    dest="$2"
    if [ -w "$(dirname "${dest}")" ] 2>/dev/null || mkdir -p "$(dirname "${dest}")" 2>/dev/null; then
        install -m 0755 "${src}" "${dest}"
    else
        run_priv mkdir -p "$(dirname "${dest}")"
        run_priv install -m 0755 "${src}" "${dest}"
    fi
}

EXTRACT_DIR="${TMPDIR_UV}/extract"
mkdir -p "${EXTRACT_DIR}"
case "${EXT}" in
    tar.gz)
        tar -xzf "${TMPDIR_UV}/${ASSET}" -C "${EXTRACT_DIR}"
        ;;
    zip)
        unzip -q -o "${TMPDIR_UV}/${ASSET}" -d "${EXTRACT_DIR}"
        ;;
esac

UV_BIN="$(find "${EXTRACT_DIR}" -type f \( -name uv -o -name uv.exe \) | head -n1)"
UVX_BIN="$(find "${EXTRACT_DIR}" -type f \( -name uvx -o -name uvx.exe \) | head -n1)"
if [ -z "${UV_BIN}" ]; then
    echo "uv binary missing from ${ASSET}" >&2
    exit 1
fi
if [ "${EXT}" = "zip" ]; then
    install_bin "${UV_BIN}" "${UV_INSTALL_DIR}/uv.exe"
    if [ -n "${UVX_BIN}" ]; then
        install_bin "${UVX_BIN}" "${UV_INSTALL_DIR}/uvx.exe"
    fi
else
    install_bin "${UV_BIN}" "${UV_INSTALL_DIR}/uv"
    if [ -n "${UVX_BIN}" ]; then
        install_bin "${UVX_BIN}" "${UV_INSTALL_DIR}/uvx"
    fi
fi

export PATH="${UV_INSTALL_DIR}:${PATH}"
uv --version
