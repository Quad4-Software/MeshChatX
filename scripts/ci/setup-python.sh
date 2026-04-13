#!/bin/sh
# Build and install Python from official python.org source.
# Verifies: OpenPGP (.asc) when present, otherwise Sigstore (.sigstore) with cosign.
# https://www.python.org/download/sigstore/  PEP 761 (3.14+): PGP removed; Sigstore only.
#
# Usage: setup-python.sh [version]
#   version: exact (3.14.x) or minor (3.14, resolved to latest patch).
set -eu

. "$(dirname "$0")/priv.sh"

# Sigstore identity and OIDC issuer per release (see python.org/download/sigstore).
sigstore_identity_for() {
    _v="$1"
    case "$_v" in
        3.7.*) echo "nad@python.org|https://github.com/login/oauth" ;;
        3.8.*|3.9.*) echo "lukasz@langa.pl|https://github.com/login/oauth" ;;
        3.10.*|3.11.*) echo "pablogsal@python.org|https://accounts.google.com" ;;
        3.12.*|3.13.*) echo "thomas@python.org|https://accounts.google.com" ;;
        3.14.*|3.15.*) echo "hugo@python.org|https://github.com/login/oauth" ;;
        3.16.*|3.17.*) echo "savannah@python.org|https://github.com/login/oauth" ;;
        3.*.*) echo "savannah@python.org|https://github.com/login/oauth" ;;
        *) echo "" ;;
    esac
}

download_cosign() {
    COSIGN_VERSION="${COSIGN_VERSION:-2.4.1}"
    COSIGN_ARCH="linux-amd64"
    case "$(uname -m)" in
        aarch64|arm64) COSIGN_ARCH="linux-arm64" ;;
        x86_64|amd64) COSIGN_ARCH="linux-amd64" ;;
        x86_64-gnu) COSIGN_ARCH="linux-amd64" ;;
        *)
            echo "unsupported uname -m for cosign: $(uname -m)" >&2
            exit 1
            ;;
    esac
    COSIGN_BIN="/tmp/cosign-${COSIGN_VERSION}-${COSIGN_ARCH}"
    if [ ! -x "$COSIGN_BIN" ]; then
        curl -fsSL "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-${COSIGN_ARCH}" \
            -o "$COSIGN_BIN"
        chmod +x "$COSIGN_BIN"
    fi
    echo "$COSIGN_BIN"
}

PY_INPUT="${1:-3.14}"

CURRENT="$(python3 --version 2>/dev/null | sed 's/Python //')" || true

case "$PY_INPUT" in
    *.*.*)
        PY_VERSION="$PY_INPUT"
        ;;
    *)
        echo "Resolving latest Python ${PY_INPUT}.x from python.org"
        PY_VERSION="$(curl -fsSL "https://www.python.org/ftp/python/" \
            | grep -o "href=\"${PY_INPUT}\.[0-9]*/" \
            | sed 's/href="//;s/\///' \
            | sort -t. -k3 -n \
            | tail -1)"
        if [ -z "$PY_VERSION" ]; then
            echo "Failed to resolve Python ${PY_INPUT}.x" >&2
            exit 1
        fi
        echo "Resolved to ${PY_VERSION}"
        ;;
esac

if [ "$CURRENT" = "$PY_VERSION" ]; then
    echo "Python ${PY_VERSION} already installed"
    python3 --version
    exit 0
fi

echo "Building Python ${PY_VERSION} from source (python.org)"

run_priv apt-get update -qq
run_priv apt-get install -y -qq \
    build-essential gnupg curl \
    libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev libffi-dev liblzma-dev libncurses-dev > /dev/null 2>&1

TARBALL="Python-${PY_VERSION}.tar.xz"
SRC_URL="https://www.python.org/ftp/python/${PY_VERSION}/${TARBALL}"
SIG_URL="${SRC_URL}.asc"

curl -fsSL "$SRC_URL" -o "/tmp/${TARBALL}"

SIG_HTTP="$(curl -sS -o "/tmp/${TARBALL}.asc" -w "%{http_code}" "$SIG_URL" || true)"
if [ "$SIG_HTTP" != "200" ]; then
    rm -f "/tmp/${TARBALL}.asc"
fi

GPG_KEYS=""
case "$PY_VERSION" in
    3.13.*|3.14.*)
        GPG_KEYS="A035C8C19219BA821ECEA86B64E628F8D684696D 7169605F62C751356D054A26A821E680E5FA6305"
        ;;
    3.11.*|3.12.*)
        GPG_KEYS="A035C8C19219BA821ECEA86B64E628F8D684696D 7169605F62C751356D054A26A821E680E5FA6305"
        ;;
    3.9.*|3.10.*)
        GPG_KEYS="E3FF2839C048B25C084DEBE9B26995E310250568"
        ;;
    *)
        echo "No known GPG key for Python ${PY_VERSION}; skipping OpenPGP signature check" >&2
        ;;
esac

GPG_VERIFIED=0
if [ "$SIG_HTTP" = "200" ] && [ -n "$GPG_KEYS" ]; then
    export GNUPGHOME="$(mktemp -d)"
    for key in $GPG_KEYS; do
        gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "$key" 2>/dev/null || \
        gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys "$key" 2>/dev/null || true
    done
    gpg --batch --verify "/tmp/${TARBALL}.asc" "/tmp/${TARBALL}"
    rm -rf "$GNUPGHOME"
    unset GNUPGHOME
    echo "OpenPGP signature verified"
    GPG_VERIFIED=1
fi

if [ "$GPG_VERIFIED" != "1" ]; then
    SIGSTORE_URL="${SRC_URL}.sigstore"
    SIGSTORE_HTTP="$(curl -sS -o "/tmp/${TARBALL}.sigstore" -w "%{http_code}" "$SIGSTORE_URL" || true)"
    if [ "$SIGSTORE_HTTP" != "200" ]; then
        rm -f "/tmp/${TARBALL}.sigstore"
        echo "No OpenPGP signature (HTTP ${SIG_HTTP}) and no Sigstore bundle at ${SIGSTORE_URL} (HTTP ${SIGSTORE_HTTP})" >&2
        exit 1
    fi
    II="$(sigstore_identity_for "$PY_VERSION")"
    if [ -z "$II" ]; then
        echo "No Sigstore identity mapping for Python ${PY_VERSION}" >&2
        exit 1
    fi
    SIG_IDENTITY="$(echo "$II" | cut -d'|' -f1)"
    SIG_ISSUER="$(echo "$II" | cut -d'|' -f2)"
    COSIGN_BIN="$(download_cosign)"
    "$COSIGN_BIN" verify-blob --new-bundle-format \
        --certificate-oidc-issuer "$SIG_ISSUER" \
        --certificate-identity "$SIG_IDENTITY" \
        --bundle "/tmp/${TARBALL}.sigstore" \
        "/tmp/${TARBALL}"
    echo "Sigstore signature verified"
fi

cd /tmp
tar -xJf "${TARBALL}"
cd "Python-${PY_VERSION}"

BUILD_LOG="/tmp/python-build.log"
./configure --prefix=/usr/local --with-ensurepip=install > "$BUILD_LOG" 2>&1
make -j"$(nproc)" >> "$BUILD_LOG" 2>&1
run_priv make install >> "$BUILD_LOG" 2>&1

run_priv ln -sf /usr/local/bin/python3 /usr/local/bin/python
run_priv ln -sf /usr/local/bin/pip3 /usr/local/bin/pip

cd /
rm -rf "/tmp/${TARBALL}" "/tmp/${TARBALL}.asc" "/tmp/${TARBALL}.sigstore" "/tmp/Python-${PY_VERSION}" "$BUILD_LOG"

python3 --version
pip3 --version
