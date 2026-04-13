#!/bin/sh
# Build and install Python from official python.org source with GPG verification.
# Source: https://www.python.org
#
# Usage: setup-python.sh [version]
#   version: exact (3.14.x) or minor (3.14, resolved to latest patch).
set -eu

. "$(dirname "$0")/priv.sh"

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
curl -fsSL "$SIG_URL" -o "/tmp/${TARBALL}.asc"

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
        echo "No known GPG key for Python ${PY_VERSION}; skipping signature check" >&2
        ;;
esac

if [ -n "$GPG_KEYS" ]; then
    export GNUPGHOME="$(mktemp -d)"
    for key in $GPG_KEYS; do
        gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "$key" 2>/dev/null || \
        gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys "$key" 2>/dev/null || true
    done
    gpg --batch --verify "/tmp/${TARBALL}.asc" "/tmp/${TARBALL}"
    rm -rf "$GNUPGHOME"
    unset GNUPGHOME
    echo "GPG signature verified"
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
rm -rf "/tmp/${TARBALL}" "/tmp/${TARBALL}.asc" "/tmp/Python-${PY_VERSION}" "$BUILD_LOG"

python3 --version
pip3 --version
