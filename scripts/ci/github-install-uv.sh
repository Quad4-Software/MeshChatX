#!/usr/bin/env bash
# Install UV from GitHub releases with SHA256 verification (no pip bootstrap).
# Set UV_VERSION to override the default. Optional UV_INSTALL_DIR (default /usr/local/bin).
set -euo pipefail

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

UV_VERSION="${UV_VERSION:-0.13.5}"
UV_INSTALL_DIR="${UV_INSTALL_DIR:-/usr/local/bin}"

if command -v uv >/dev/null 2>&1; then
    _uv_have="$(uv --version 2>/dev/null | awk '{print $2}' || true)"
    if [ "${_uv_have}" = "${UV_VERSION}" ]; then
        echo "uv ${UV_VERSION} already installed"
        exit 0
    fi
fi
unset _uv_have

# /usr/local/bin is not writable on all self-hosted runners and sudo may be
# unusable (no_new_privs). Prefer the persistent per-user dir so the binary
# is fetched once instead of every job; RUNNER_TEMP is the last resort.
if [ "$(id -u)" -ne 0 ] && [ ! -w "${UV_INSTALL_DIR}" ] && ! sudo -n true 2>/dev/null; then
    if mkdir -p "${HOME}/.local/bin" 2>/dev/null && [ -w "${HOME}/.local/bin" ]; then
        UV_INSTALL_DIR="${HOME}/.local/bin"
    else
        UV_INSTALL_DIR="${RUNNER_TEMP:-${HOME}/.local}/bin"
    fi
fi

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Alpine/musl needs the musl release tarball. A glibc binary on musl exits 127
# ("not found") because the dynamic linker path is missing.
linux_libc() {
    if [ -f /etc/alpine-release ]; then
        echo musl
        return
    fi
    if command -v ldd >/dev/null 2>&1; then
        case "$(ldd --version 2>&1 | head -n1)" in
            *[Mm]usl*)
                echo musl
                return
                ;;
        esac
        if ldd /bin/sh 2>&1 | head -n1 | grep -qi musl; then
            echo musl
            return
        fi
    fi
    echo gnu
}

case "${OS}" in
    linux)
        LIBC="$(linux_libc)"
        case "${ARCH}-${LIBC}" in
            x86_64-gnu) TARGET="x86_64-unknown-linux-gnu" ;;
            x86_64-musl) TARGET="x86_64-unknown-linux-musl" ;;
            aarch64-gnu) TARGET="aarch64-unknown-linux-gnu" ;;
            aarch64-musl) TARGET="aarch64-unknown-linux-musl" ;;
            *)
                echo "Unsupported Linux arch/libc: ${ARCH}/${LIBC}" >&2
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
EXTRACT_DIR="${TMPDIR_UV}/extract"
mkdir -p "${EXTRACT_DIR}"

GITHUB_OK=0
if download "${TMPDIR_UV}/${ASSET}" "${BASE_URL}/${ASSET}" &&
    download "${TMPDIR_UV}/${ASSET}.sha256" "${BASE_URL}/${ASSET}.sha256"; then
    GITHUB_OK=1
fi

if [ "${GITHUB_OK}" = "1" ]; then
    EXPECTED="$(awk '{print $1}' "${TMPDIR_UV}/${ASSET}.sha256")"
    ACTUAL="$(sha256sum "${TMPDIR_UV}/${ASSET}" | awk '{print $1}')"
    if [ -z "${EXPECTED}" ] || [ "${EXPECTED}" != "${ACTUAL}" ]; then
        echo "SHA256 verification failed for ${ASSET}" >&2
        echo "  expected: ${EXPECTED}" >&2
        echo "  got:      ${ACTUAL}" >&2
        exit 1
    fi
    echo "SHA256 verified: ${ACTUAL}"
    case "${EXT}" in
        tar.gz)
            tar -xzf "${TMPDIR_UV}/${ASSET}" -C "${EXTRACT_DIR}"
            ;;
        zip)
            unzip -q -o "${TMPDIR_UV}/${ASSET}" -d "${EXTRACT_DIR}"
            ;;
    esac
else
    # GitHub release assets can be unavailable (e.g. 504 outages) while
    # PyPI stays up. The uv wheel ships the same binaries under
    # <ver>.data/scripts/, so reuse the shared find/install below.
    echo "GitHub release download failed; trying PyPI wheel fallback" >&2
    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 is required for the PyPI fallback" >&2
        exit 1
    fi
    WHEEL_PICK="$(curl -fsSL --retry 3 --retry-all-errors \
        --connect-timeout 20 --max-time 60 \
        "https://pypi.org/pypi/uv/${UV_VERSION}/json" | UV_TARGET="${TARGET}" python3 -c '
import json, os, sys
target = os.environ["UV_TARGET"]
def ok(fn):
    fn = fn.lower()
    if target == "x86_64-unknown-linux-gnu":
        return "x86_64" in fn and "manylinux" in fn and "musllinux" not in fn
    if target == "x86_64-unknown-linux-musl":
        return "x86_64" in fn and "musllinux" in fn
    if target == "aarch64-unknown-linux-gnu":
        return "aarch64" in fn and "manylinux" in fn
    if target == "aarch64-unknown-linux-musl":
        return "aarch64" in fn and "musllinux" in fn
    if target == "x86_64-apple-darwin":
        return "macosx" in fn and "x86_64" in fn
    if target == "aarch64-apple-darwin":
        return "macosx" in fn and "arm64" in fn
    if target == "x86_64-pc-windows-msvc":
        return "win_amd64" in fn
    if target == "aarch64-pc-windows-msvc":
        return "win_arm64" in fn
    return False
d = json.load(sys.stdin)
cands = [u for u in d.get("urls", [])
         if u.get("filename", "").endswith(".whl") and ok(u["filename"])]
if not cands:
    sys.exit("no matching PyPI wheel for " + target)
cands.sort(key=lambda u: u["filename"])
u = cands[0]
print(u["url"], u["digests"]["sha256"])
')" || {
        echo "PyPI fallback failed: could not select a wheel" >&2
        exit 1
    }
    WHEEL_URL="${WHEEL_PICK%% *}"
    WHEEL_SHA256="${WHEEL_PICK##* }"
    download "${TMPDIR_UV}/uv.whl" "${WHEEL_URL}"
    echo "${WHEEL_SHA256}  ${TMPDIR_UV}/uv.whl" | sha256sum -c --status || {
        echo "SHA256 verification failed for PyPI wheel ${WHEEL_URL}" >&2
        exit 1
    }
    echo "SHA256 verified (PyPI): ${WHEEL_SHA256}"
    python3 -m zipfile -e "${TMPDIR_UV}/uv.whl" "${EXTRACT_DIR}/"
fi

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
if [ "${EXT}" = "zip" ]; then
    UV_CMD="${UV_INSTALL_DIR}/uv.exe"
else
    UV_CMD="${UV_INSTALL_DIR}/uv"
fi
if [ ! -x "${UV_CMD}" ] && [ ! -f "${UV_CMD}" ]; then
    echo "uv install failed: missing executable at ${UV_CMD}" >&2
    exit 1
fi
"${UV_CMD}" --version

# Persist for later workflow steps. Linux runners usually already have
# /usr/local/bin. Windows Git Bash does not keep the install-step PATH.
if [ -n "${GITHUB_PATH:-}" ]; then
    echo "${UV_INSTALL_DIR}" >> "${GITHUB_PATH}"
fi
