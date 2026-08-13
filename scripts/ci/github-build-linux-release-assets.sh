#!/usr/bin/env bash
# Build wheel, Linux AppImage/deb (x64 + arm64), optional RPM/APK, frontend zip, and SBOM under ./release-assets/.
# Expects repo root as cwd, dependencies installed (task install / pnpm), and meshchatx/public populated when building Electron.
# Optional: SKIP_WHEEL=1, SKIP_ELECTRON=1, TRIVY_SBOM=0
# Optional: MESHCHATX_LINUX_FORMATS = comma list of appimage,deb,rpm,apk (default: all four)
set -euo pipefail

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
    LINUX_FORMATS="appimage,deb,rpm,apk"
fi

has_format() {
    case ",$LINUX_FORMATS," in
        *",$1,"*) return 0 ;;
        *) return 1 ;;
    esac
}

for _fmt in ${LINUX_FORMATS//,/ }; do
    case "$_fmt" in
        appimage|deb|rpm|apk) ;;
        *)
            echo "Unknown Linux package format '$_fmt' in MESHCHATX_LINUX_FORMATS (expected appimage, deb, rpm, apk, or all)" >&2
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

# Retry electron-builder when GitHub CDN drops the TLS stream (ECONNRESET).
# Freeze already finished. This only re-runs packaging.
run_electron_builder() {
    _max="${ELECTRON_BUILDER_RETRIES:-5}"
    _n=1
    _delay=8
    while true; do
        _log="$(mktemp)"
        set +e
        pnpm exec electron-builder "$@" 2>&1 | tee "$_log"
        _status="${PIPESTATUS[0]}"
        set -e
        if [ "$_status" -eq 0 ]; then
            rm -f "$_log"
            return 0
        fi
        if [ "$_n" -ge "$_max" ]; then
            echo "electron-builder failed after ${_n} attempt(s)" >&2
            rm -f "$_log"
            return "$_status"
        fi
        if ! grep -Eqi 'ECONNRESET|ETIMEDOUT|ECONNREFUSED|ENOTFOUND|EPIPE|socket hang up|RequestError' "$_log"; then
            rm -f "$_log"
            return "$_status"
        fi
        echo "electron-builder hit a transient network error (attempt ${_n}/${_max}). Retrying in ${_delay}s." >&2
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

if [ "${SKIP_ELECTRON:-0}" != 1 ]; then
    if [ -n "$appimage_deb_targets" ]; then
        if has_format appimage; then
            bash scripts/ci/github-warm-appimage-tools.sh
        fi
        pnpm run electron-postinstall
        if [ "$NATIVE_ARCH" = "x64" ]; then
            echo "Electron linux x64 ($appimage_deb_targets)..."
            PLATFORM=linux ARCH=x64 pnpm run build
            # shellcheck disable=SC2086
            run_electron_builder --linux $appimage_deb_targets --x64 --publish=never
        elif [ "$NATIVE_ARCH" = "arm64" ]; then
            echo "Electron linux arm64 ($appimage_deb_targets)..."
            PLATFORM=linux ARCH=arm64 pnpm run build
            # shellcheck disable=SC2086
            run_electron_builder --linux $appimage_deb_targets --arm64 --publish=never
        fi
    else
        echo "Skipping AppImage/deb (not selected in MESHCHATX_LINUX_FORMATS)."
    fi

    if [ "$NATIVE_ARCH" = "x64" ]; then
        if has_format rpm; then
            echo "RPM (best-effort)..."
            if ! task dist:fe:rpm; then
                echo "RPM build failed or skipped; continuing." >&2
            fi
        fi
        if has_format apk; then
            echo "APK (best-effort)..."
            if ! task dist:fe:apk; then
                echo "APK build failed or skipped; continuing." >&2
            fi
        fi
    elif has_format rpm || has_format apk; then
        echo "Skipping RPM/APK on $NATIVE_ARCH runner (built on x64 only)." >&2
    fi
else
    echo "Skipping Electron packages (SKIP_ELECTRON=1)."
fi

echo "Collecting release files..."
find dist -maxdepth 1 -type f \( -name "*-linux*.AppImage" -o -name "*-linux*.deb" -o -name "*-linux*.rpm" -o -name "*-linux*.apk" \) -exec cp -f {} release-assets/ \; 2>/dev/null || true
find python-dist -maxdepth 1 -type f -name "*.whl" -exec cp -f {} release-assets/ \; 2>/dev/null || true

if [ -d meshchatx/public ] && [ "${SKIP_ELECTRON:-0}" != 1 ]; then
    ( cd meshchatx/public && zip -qr "${ROOT}/release-assets/meshchatx-frontend.zip" . )
fi

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

echo "github-build-linux-release-assets.sh: done; see ./release-assets/"
