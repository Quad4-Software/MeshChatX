#!/usr/bin/env bash
# Build wheel, Python PYZ, Linux AppImage/deb (x64 + arm64), optional RPM/APK, frontend zip, and SBOM under ./release-assets/.
# Expects repo root as cwd, dependencies installed (task install / pnpm), and meshchatx/public populated when building the desktop shell.
# Optional: SKIP_WHEEL=1, SKIP_PYZ=1, SKIP_DESKTOP=1, TRIVY_SBOM=0
# Optional: MESHCHATX_LINUX_FORMATS = comma list of appimage,deb,rpm (default: all four)
set -euo pipefail

# Self-hosted runners may lack /tmp; mktemp honours TMPDIR.
if [ ! -d /tmp ] || [ ! -w /tmp ]; then
    _ci_tmp="${RUNNER_TEMP:-${HOME}/.meshchatx-ci}/tmp"
    mkdir -p "${_ci_tmp}" 2>/dev/null && {
        TMPDIR="${_ci_tmp}"
        export TMPDIR
        [ -n "${GITHUB_ENV:-}" ] && echo "TMPDIR=${TMPDIR}" >> "${GITHUB_ENV}"
    }
fi
unset _ci_tmp


ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/ci-node-path.sh
. "$(dirname "$0")/ci-node-path.sh"

require_node_min() {
    _min_major="${1:-22}"
    _ver="$(node -v 2>/dev/null || true)"
    _major="${_ver#v}"
    _major="${_major%%.*}"
    if [ -z "$_major" ] || [ "$_major" -lt "$_min_major" ]; then
        echo "Node.js ${_min_major}+ required (got: ${_ver:-unknown}); check PATH does not prefer /usr/local/bin over setup-node." >&2
        command -v node >&2 || true
        exit 1
    fi
}

require_node_min 24

mkdir -p release-assets

HOST_ARCH="$(uname -m)"
case "$HOST_ARCH" in
    x86_64) NATIVE_ARCH="x64" ;;
    aarch64|arm64) NATIVE_ARCH="arm64" ;;
    *) NATIVE_ARCH="$HOST_ARCH" ;;
esac

LINUX_FORMATS="${MESHCHATX_LINUX_FORMATS:-all}"
if [ "$LINUX_FORMATS" = "all" ]; then
    LINUX_FORMATS="appimage,deb,rpm"
fi

has_format() {
    case ",$LINUX_FORMATS," in
        *",$1,"*) return 0 ;;
        *) return 1 ;;
    esac
}

for _fmt in ${LINUX_FORMATS//,/ }; do
    case "$_fmt" in
        appimage|deb|rpm) ;;
        *)
            echo "Unknown Linux package format '$_fmt' in MESHCHATX_LINUX_FORMATS (expected appimage, deb, rpm, or all)" >&2
            exit 1
            ;;
    esac
done

appimage_deb_targets=""
has_format appimage && appimage_deb_targets="$appimage_deb_targets AppImage"
has_format deb && appimage_deb_targets="$appimage_deb_targets deb"
appimage_deb_targets="${appimage_deb_targets# }"

if [ -n "${GITHUB_TOKEN:-}" ] && [ -z "${GH_TOKEN:-}" ]; then
    export GH_TOKEN="$GITHUB_TOKEN"
fi

# Retry desktop packaging when the network drops (Go module/tool downloads).
run_desktop_package() {
    _max="${DESKTOP_PACKAGE_RETRIES:-5}"
    _n=1
    _delay=8
    while true; do
        _log="$(mktemp)"
        set +e
        ( cd desktop && task "$@" ) 2>&1 | tee "$_log"
        _status="${PIPESTATUS[0]}"
        set -e
        if [ "$_status" -eq 0 ]; then
            rm -f "$_log"
            return 0
        fi
        if [ "$_n" -ge "$_max" ]; then
            echo "desktop packaging failed after ${_n} attempt(s)" >&2
            rm -f "$_log"
            return "$_status"
        fi
        if ! grep -Eqi 'ECONNRESET|ETIMEDOUT|ECONNREFUSED|ENOTFOUND|EPIPE|socket hang up|RequestError|i/o timeout' "$_log"; then
            rm -f "$_log"
            return "$_status"
        fi
        echo "desktop packaging hit a transient network error (attempt ${_n}/${_max}). Retrying in ${_delay}s." >&2
        rm -f "$_log"
        sleep "$_delay"
        _n=$((_n + 1))
        _delay=$((_delay * 2))
        if [ "$_delay" -gt 60 ]; then
            _delay=60
        fi
    done
}

if [ "${SKIP_WHEEL:-0}" != 1 ]; then
    if [ "$NATIVE_ARCH" = "x64" ]; then
        echo "Building Python wheel..."
        task build:wheel
    else
        echo "Skipping wheel on $NATIVE_ARCH runner (pure-Python wheel built on x64)."
    fi
else
    echo "Skipping wheel (SKIP_WHEEL=1)."
fi

build_pyz() {
    local pyver="$1"
    local shebang="/usr/bin/env python${pyver}"
    local output="release-assets/meshchatx-py${pyver//./}-linux-${NATIVE_ARCH}.pyz"
    PYZ_PYTHON_VERSION="$pyver" \
        PYZ_SHEBANG="$shebang" \
        PYZ_OUTPUT="$output" \
        SKIP_WHEEL="$2" \
        bash scripts/build-pyz.sh
}

if [ "${SKIP_PYZ:-0}" != 1 ]; then
    echo "Building Python PYZs..."
    _skip_wheel=0
    if [ "$NATIVE_ARCH" = "x64" ]; then
        _skip_wheel=1
    fi
    for _py in 3.11 3.15; do
        build_pyz "$_py" "$_skip_wheel"
        _skip_wheel=1
    done
else
    echo "Skipping Python PYZ (SKIP_PYZ=1)."
fi

if [ "${SKIP_DESKTOP:-0}" != 1 ]; then
    if [ -n "$appimage_deb_targets" ]; then
        if [ "${MESHCHATX_FRONTEND_PREBUILT:-0}" = "1" ]; then
            if [[ ! -f "meshchatx/public/index.html" ]]; then
                echo "MESHCHATX_FRONTEND_PREBUILT=1 but meshchatx/public/index.html is missing." >&2
                exit 1
            fi
            echo "Reusing prebuilt frontend assets in meshchatx/public/."
            _desktop_backend() {
                PLATFORM=linux ARCH="$1" pnpm run build-backend
            }
        else
            _desktop_backend() {
                PLATFORM=linux ARCH="$1" pnpm run build
            }
        fi
        _goarch="${NATIVE_ARCH/x64/amd64}"
        _tasks=""
        has_format appimage && _tasks="$_tasks linux:create:appimage"
        has_format deb && _tasks="$_tasks linux:create:deb linux:create:rpm"
        if [ -n "$_tasks" ]; then
            echo "Desktop linux ${NATIVE_ARCH} (${_tasks})..."
            _desktop_backend "${NATIVE_ARCH/x64/amd64}"
            # shellcheck disable=SC2086
            run_desktop_package $_tasks ARCH="$_goarch"
        fi
        if [[ -d "desktop/bin/backend" ]]; then
            node scripts/ci/github-verify-backend-manifest.mjs desktop/bin/backend
        fi
    else
        echo "Skipping AppImage/deb (not selected in MESHCHATX_LINUX_FORMATS)."
    fi

    if [ "$NATIVE_ARCH" = "x64" ]; then
        : # deb+rpm produced by linux:package above
    elif has_format rpm; then
        echo "Skipping RPM on $NATIVE_ARCH runner (built on x64 only)." >&2
    fi
else
    echo "Skipping desktop packages (SKIP_DESKTOP=1)."
fi

echo "Collecting release files..."
find desktop/bin -maxdepth 1 -type f \( -name "*.AppImage" -o -name "*.deb" -o -name "*.rpm" -o -name "*.zip" \) -exec cp -f {} release-assets/ \; 2>/dev/null || true
find python-dist -maxdepth 1 -type f -name "*.whl" -exec cp -f {} release-assets/ \; 2>/dev/null || true

if [ -d meshchatx/public ] && [ "${SKIP_DESKTOP:-0}" != 1 ]; then
    ( cd meshchatx/public && zip -qr "${ROOT}/release-assets/meshchatx-frontend.zip" . )
fi

# Print what actually ships so a silently skipped format is visible in the
# release log instead of only in the asset list.
echo "release-assets contents:"
ls -1 release-assets/

{
    echo "## Integrity"
    echo ""
    echo "Each artifact may have a matching **\`*.cosign.bundle\`** when repository signing secrets are configured (see SECURITY.md)."
    echo ""
    echo "SBOM: **\`sbom.cyclonedx.json\`** (CycloneDX) when produced by CI."
} > release-body.md

if [ "${TRIVY_SBOM:-1}" != 0 ] && command -v trivy >/dev/null 2>&1; then
    echo "Generating SBOM..."
    trivy fs --format cyclonedx --include-dev-deps --output release-assets/sbom.cyclonedx.json .
else
    echo "Skipping SBOM (trivy not on PATH or TRIVY_SBOM=0)." >&2
fi

# Ship the curated OpenVEX document alongside the SBOM so downstream
# scanners (grype --vex, Dependency-Track) can consume our triage notes.
if [ -f security/openvex.json ]; then
    cp -f security/openvex.json release-assets/openvex.json
fi

echo "github-build-linux-release-assets.sh: done; see ./release-assets/"
