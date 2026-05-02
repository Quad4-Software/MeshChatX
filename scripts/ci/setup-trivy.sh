#!/bin/sh
# Install Trivy .deb for CI (scan / docker workflows).
#
# Default (no TRIVY_DEB_URL): official assets from
# https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/
#   1) cosign verify-blob on trivy_${VER}_checksums.txt (+ .sigstore.json)
#   2) sha256sum -c for the arch .deb using that checksums file
#   3) cosign verify-blob on the .deb (+ .deb.sigstore.json)
#
# Optional mirror: TRIVY_DEB_URL and TRIVY_DEB_SHA256 (sha256sum -c format, hex only).
set -eu

COSIGN_VERSION="${COSIGN_VERSION:-3.0.6}"
TRIVY_VERSION="${TRIVY_VERSION:-0.69.3}"
TRIVY_RELEASE_BASE="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}"
# Keyless signing identity for aquasecurity/trivy reusable release workflow (any semver tag).
TRIVY_CERT_IDENTITY_RE='^https://github.com/aquasecurity/trivy/\.github/workflows/reusable-release\.yaml@refs/tags/v[0-9]+\.[0-9]+\.[0-9]+$'
TRIVY_CERT_ISSUER_RE='^https://token\.actions\.githubusercontent\.com$'

ensure_cosign() {
    if command -v cosign >/dev/null 2>&1; then
        return 0
    fi
    sh scripts/ci/setup-cosign.sh "${COSIGN_VERSION}"
}

verify_upstream_deb() {
    deb_arch="$1"
    DEB_BASE="trivy_${TRIVY_VERSION}_${deb_arch}.deb"

    ensure_cosign
    export COSIGN_YES="${COSIGN_YES:-true}"

    curl -fsSL -o /tmp/trivy_checksums.txt "${TRIVY_RELEASE_BASE}/trivy_${TRIVY_VERSION}_checksums.txt"
    curl -fsSL -o /tmp/trivy_checksums.sigstore.json "${TRIVY_RELEASE_BASE}/trivy_${TRIVY_VERSION}_checksums.txt.sigstore.json"
    cosign verify-blob /tmp/trivy_checksums.txt --bundle /tmp/trivy_checksums.sigstore.json \
        --certificate-identity-regexp="${TRIVY_CERT_IDENTITY_RE}" \
        --certificate-oidc-issuer-regexp="${TRIVY_CERT_ISSUER_RE}"

    EXPECTED_SHA="$(awk -v f="${DEB_BASE}" '$2 == f { print $1; exit }' /tmp/trivy_checksums.txt)"
    if [ -z "${EXPECTED_SHA}" ]; then
        echo "setup-trivy.sh: no SHA256 line for ${DEB_BASE} in checksums.txt" >&2
        exit 1
    fi

    curl -fsSL -o /tmp/trivy.deb "${TRIVY_RELEASE_BASE}/${DEB_BASE}"
    echo "${EXPECTED_SHA}  /tmp/trivy.deb" | sha256sum -c

    curl -fsSL -o /tmp/trivy.deb.sigstore.json "${TRIVY_RELEASE_BASE}/${DEB_BASE}.sigstore.json"
    cosign verify-blob /tmp/trivy.deb --bundle /tmp/trivy.deb.sigstore.json \
        --certificate-identity-regexp="${TRIVY_CERT_IDENTITY_RE}" \
        --certificate-oidc-issuer-regexp="${TRIVY_CERT_ISSUER_RE}"

    rm -f /tmp/trivy_checksums.txt /tmp/trivy_checksums.sigstore.json /tmp/trivy.deb.sigstore.json
}

if [ -n "${TRIVY_DEB_URL:-}" ]; then
    if [ -z "${TRIVY_DEB_SHA256:-}" ]; then
        echo "setup-trivy.sh: TRIVY_DEB_URL requires TRIVY_DEB_SHA256" >&2
        exit 1
    fi
    curl -fsSL -o /tmp/trivy.deb "${TRIVY_DEB_URL}"
    echo "${TRIVY_DEB_SHA256}  /tmp/trivy.deb" | sha256sum -c
else
    arch="$(uname -m)"
    deb_arch=
    case "$arch" in
        x86_64|amd64) deb_arch=Linux-64bit ;;
        aarch64|arm64) deb_arch=Linux-ARM64 ;;
        armv7l|armv6l|armhf) deb_arch=Linux-ARM ;;
        *)
            echo "setup-trivy.sh: unsupported uname -m: ${arch} (set TRIVY_DEB_URL)" >&2
            exit 1
            ;;
    esac
    verify_upstream_deb "${deb_arch}"
fi

sh scripts/ci/exec-priv.sh dpkg -i /tmp/trivy.deb || sh scripts/ci/exec-priv.sh apt-get install -f -y
trivy --version
