#!/bin/sh
# Install Adoptium Temurin JDK with SHA256 verification.
# Uses the Adoptium assets API to obtain the checksum and download URL
# directly from the source, avoiding opaque redirects.
# Source: https://adoptium.net (Eclipse Foundation)
# Usage: setup-java.sh [major_version]
set -eu

. "$(dirname "$0")/priv.sh"

JAVA_VERSION="${1:-17}"

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="x64" ;;
    aarch64) ARCH="aarch64" ;;
    *)       echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

echo "Installing Temurin JDK ${JAVA_VERSION} (${ARCH})"

ASSETS_API="https://api.adoptium.net/v3/assets/latest/${JAVA_VERSION}/hotspot?architecture=${ARCH}&image_type=jdk&os=linux&vendor=eclipse"
API_JSON="$(curl -fsSL "$ASSETS_API")"

DOWNLOAD_URL="$(echo "$API_JSON" | sed -n 's/.*"link" *: *"\([^"]*\)".*/\1/p' | head -1)"
CHECKSUM_URL="$(echo "$API_JSON" | sed -n 's/.*"checksum_link" *: *"\([^"]*\)".*/\1/p' | head -1)"
EXPECTED="$(echo "$API_JSON" | sed -n 's/.*"checksum" *: *"\([0-9a-f]*\)".*/\1/p' | head -1)"

if [ -z "$DOWNLOAD_URL" ] || [ -z "$EXPECTED" ]; then
    echo "Failed to resolve Temurin JDK ${JAVA_VERSION} for ${ARCH}" >&2
    exit 1
fi

curl -fsSL "$DOWNLOAD_URL" -o /tmp/jdk.tar.gz

ACTUAL="$(sha256sum /tmp/jdk.tar.gz | cut -d' ' -f1)"
if [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "SHA256 verification failed for JDK ${JAVA_VERSION}" >&2
    echo "  expected: ${EXPECTED}" >&2
    echo "  got:      ${ACTUAL}" >&2
    rm -f /tmp/jdk.tar.gz
    exit 1
fi
echo "SHA256 verified: ${ACTUAL}"

if [ -n "$CHECKSUM_URL" ]; then
    EXPECTED_LINK="$(curl -fsSL "$CHECKSUM_URL" | cut -d' ' -f1)"
    if [ "$EXPECTED_LINK" != "$ACTUAL" ]; then
        echo "Cross-check against checksum_link also failed" >&2
        rm -f /tmp/jdk.tar.gz
        exit 1
    fi
    echo "Cross-verified against checksum_link"
fi

run_priv mkdir -p /opt/java
run_priv tar -xzf /tmp/jdk.tar.gz -C /opt/java --strip-components=1
rm -f /tmp/jdk.tar.gz

CI_ENV="${GITEA_ENV:-${GITHUB_ENV:-/dev/null}}"
CI_PATH="${GITEA_PATH:-${GITHUB_PATH:-/dev/null}}"
echo "JAVA_HOME=/opt/java" >> "$CI_ENV"
echo "/opt/java/bin" >> "$CI_PATH"

export JAVA_HOME=/opt/java
export PATH="/opt/java/bin:$PATH"
java -version
