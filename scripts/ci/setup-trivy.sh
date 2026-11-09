#!/bin/sh
# Install Trivy for CI (scan / docker workflows).
#
# Default (no TRIVY_DEB_URL): official assets from
# https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/
#   1) cosign verify-blob on trivy_${VER}_checksums.txt (+ .sigstore.json)
#   2) sha256sum -c for the arch asset using that checksums file
#   3) cosign verify-blob on the asset (+ .sigstore.json)
#
# Debian-family runners (dpkg present) install the .deb via exec-priv.sh.
# Other systems (Arch, minimal containers) get the static tarball extracted
# to ${TRIVY_BIN_DIR:-$HOME/.local/bin} and added to GITHUB_PATH.
#
# Optional mirror: TRIVY_DEB_URL and TRIVY_DEB_SHA256 (sha256sum -c format, hex only).
set -eu

# /tmp can disappear mid-run on self-hosted runners (tmpfiles cleanup,
# unmounted tmpfs), so never depend on it: mktemp and friends honour
# TMPDIR. Always point TMPDIR at a user-writable per-job dir and
# propagate it to later steps via GITHUB_ENV.
_ci_tmp=""
for _ci_cand in "${RUNNER_TEMP:-}" "${HOME:-}" "${GITHUB_WORKSPACE:-}"; do
    [ -n "${_ci_cand}" ] || continue
    _ci_cand="${_ci_cand}/.meshchatx-ci-tmp"
    if mkdir -p "${_ci_cand}" 2>/dev/null && [ -w "${_ci_cand}" ]; then
        _ci_tmp="${_ci_cand}"
        break
    fi
done
if [ -n "${_ci_tmp}" ]; then
    TMPDIR="${_ci_tmp}"
    export TMPDIR
    [ -n "${GITHUB_ENV:-}" ] && echo "TMPDIR=${TMPDIR}" >> "${GITHUB_ENV}"
    echo "ci: TMPDIR=${TMPDIR}"
else
    echo "ci: WARNING: no writable temp dir available" >&2
fi
unset _ci_cand
unset _ci_tmp

COSIGN_VERSION="${COSIGN_VERSION:-3.0.6}"
TRIVY_VERSION="${TRIVY_VERSION:-0.74.0}"
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

verify_checksums() {
    ensure_cosign
    export COSIGN_YES="${COSIGN_YES:-true}"

    curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/trivy_checksums.txt "${TRIVY_RELEASE_BASE}/trivy_${TRIVY_VERSION}_checksums.txt"
    curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/trivy_checksums.sigstore.json "${TRIVY_RELEASE_BASE}/trivy_${TRIVY_VERSION}_checksums.txt.sigstore.json"
    cosign verify-blob ${TMPDIR:-/tmp}/trivy_checksums.txt --bundle ${TMPDIR:-/tmp}/trivy_checksums.sigstore.json \
        --certificate-identity-regexp="${TRIVY_CERT_IDENTITY_RE}" \
        --certificate-oidc-issuer-regexp="${TRIVY_CERT_ISSUER_RE}"
}

verify_asset() {
    asset="$1"
    out="$2"
    EXPECTED_SHA="$(awk -v f="${asset}" '$2 == f { print $1; exit }' ${TMPDIR:-/tmp}/trivy_checksums.txt)"
    if [ -z "${EXPECTED_SHA}" ]; then
        echo "setup-trivy.sh: no SHA256 line for ${asset} in checksums.txt" >&2
        exit 1
    fi

    curl -fsSL --retry 5 --retry-delay 2 -o "${out}" "${TRIVY_RELEASE_BASE}/${asset}"
    echo "${EXPECTED_SHA}  ${out}" | sha256sum -c

    curl -fsSL --retry 5 --retry-delay 2 -o "${out}.sigstore.json" "${TRIVY_RELEASE_BASE}/${asset}.sigstore.json"
    cosign verify-blob "${out}" --bundle "${out}.sigstore.json" \
        --certificate-identity-regexp="${TRIVY_CERT_IDENTITY_RE}" \
        --certificate-oidc-issuer-regexp="${TRIVY_CERT_ISSUER_RE}"
}

verify_upstream_deb() {
    deb_arch="$1"
    DEB_BASE="trivy_${TRIVY_VERSION}_${deb_arch}.deb"

    verify_checksums
    verify_asset "${DEB_BASE}" ${TMPDIR:-/tmp}/trivy.deb

    rm -f ${TMPDIR:-/tmp}/trivy_checksums.txt ${TMPDIR:-/tmp}/trivy_checksums.sigstore.json ${TMPDIR:-/tmp}/trivy.deb.sigstore.json
}

install_tgz() {
    rel_arch="$1"
    TGZ_BASE="trivy_${TRIVY_VERSION}_${rel_arch}.tar.gz"
    dest="${TRIVY_BIN_DIR:-${HOME}/.local/bin}"

    verify_checksums
    verify_asset "${TGZ_BASE}" ${TMPDIR:-/tmp}/trivy.tar.gz

    rm -f ${TMPDIR:-/tmp}/trivy_checksums.txt ${TMPDIR:-/tmp}/trivy_checksums.sigstore.json ${TMPDIR:-/tmp}/trivy.tar.gz.sigstore.json

    mkdir -p "${dest}"
    tar -xzf ${TMPDIR:-/tmp}/trivy.tar.gz -C "${dest}" trivy
    chmod +x "${dest}/trivy"
    rm -f ${TMPDIR:-/tmp}/trivy.tar.gz

    if [ -n "${GITHUB_PATH:-}" ]; then
        echo "${dest}" >> "${GITHUB_PATH}"
    fi
    PATH="${dest}:${PATH}"
    export PATH
}

arch="$(uname -m)"
rel_arch=
case "$arch" in
    x86_64|amd64) rel_arch=Linux-64bit ;;
    aarch64|arm64) rel_arch=Linux-ARM64 ;;
    armv7l|armv6l|armhf) rel_arch=Linux-ARM ;;
    *)
        echo "setup-trivy.sh: unsupported uname -m: ${arch} (set TRIVY_DEB_URL)" >&2
        exit 1
        ;;
esac

if [ -n "${TRIVY_DEB_URL:-}" ]; then
    if [ -z "${TRIVY_DEB_SHA256:-}" ]; then
        echo "setup-trivy.sh: TRIVY_DEB_URL requires TRIVY_DEB_SHA256" >&2
        exit 1
    fi
    curl -fsSL --retry 5 --retry-delay 2 -o ${TMPDIR:-/tmp}/trivy.deb "${TRIVY_DEB_URL}"
    echo "${TRIVY_DEB_SHA256}  ${TMPDIR:-/tmp}/trivy.deb" | sha256sum -c
    sh scripts/ci/exec-priv.sh dpkg -i ${TMPDIR:-/tmp}/trivy.deb || sh scripts/ci/exec-priv.sh apt-get install -f -y
elif command -v dpkg >/dev/null 2>&1; then
    verify_upstream_deb "${rel_arch}"
    sh scripts/ci/exec-priv.sh dpkg -i ${TMPDIR:-/tmp}/trivy.deb || sh scripts/ci/exec-priv.sh apt-get install -f -y
else
    install_tgz "${rel_arch}"
fi

trivy --version
