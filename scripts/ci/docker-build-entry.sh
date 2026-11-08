#!/usr/bin/env bash
# Run inside docker/Dockerfile.build after COPY. Writes outputs to /artifacts.
# Env: MESHCHATX_BUILD_TARGETS = all | wheel | desktop (desktop = Linux Wails packages, no wheel)
# Env: MESHCHATX_LINUX_FORMATS = comma list of appimage,deb,rpm (default: all three)
set -euo pipefail

cd /src

export UV_VERSION="${UV_VERSION:-0.13.5}"
export PNPM_VERSION="${PNPM_VERSION:-12.15.0}"
export WAILS3_VERSION="${WAILS3_VERSION:-v3.1.0}"

apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates curl git jq unzip xz-utils \
    build-essential pkg-config python3-dev \
    golang-go libgtk-4-dev libwebkitgtk-6.0-dev libsoup-3.0-dev \
    libfuse2 zstd

install_desktop_build_libs() {
    # gstreamer plugin packages are needed so the AppImage bundles a complete
    # plugin set (linuxdeploy-plugin-gstreamer copies the host's plugins).
    apt-get install -y --no-install-recommends \
        libgtk-4-1 libwebkitgtk-6.0-4 libsoup-3.0-0 \
        gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav
}

if ! command -v node >/dev/null 2>&1; then
    bash scripts/ci/install-node-tarball.sh
fi

sh scripts/ci/setup-task.sh "${TASK_VERSION:-3.54.0}"

corepack enable
corepack prepare "pnpm@${PNPM_VERSION}" --activate

bash scripts/ci/github-install-uv.sh

# wails3 CLI for the desktop shell build/package tasks
if ! command -v wails3 >/dev/null 2>&1; then
    go install "github.com/wailsapp/wails/v3/cmd/wails3@${WAILS3_VERSION}"
    export PATH="$PATH:$(go env GOPATH)/bin"
fi

export TRIVY_SBOM=0

targets="${MESHCHATX_BUILD_TARGETS:-all}"
case "$targets" in
    wheel)
        bash scripts/ci/github-install-deps.sh
        export SKIP_DESKTOP=1
        bash scripts/ci/github-build-linux-release-assets.sh
        ;;
    desktop)
        install_desktop_build_libs
        bash scripts/ci/github-apt-linux-packaging.sh
        bash scripts/ci/github-install-deps.sh
        task build:frontend
        export SKIP_WHEEL=1
        export SKIP_DESKTOP=0
        bash scripts/ci/github-build-linux-release-assets.sh
        ;;
    all|*)
        install_desktop_build_libs
        bash scripts/ci/github-apt-linux-packaging.sh
        bash scripts/ci/github-install-deps.sh
        task build:frontend
        export SKIP_WHEEL=0
        export SKIP_DESKTOP=0
        bash scripts/ci/github-build-linux-release-assets.sh
        ;;
esac

mkdir -p /artifacts
sh -c 'cp -a /src/release-assets/. /artifacts/ 2>/dev/null || true'
if [ -z "$(ls -A /artifacts 2>/dev/null || true)" ]; then
    echo "docker-build-entry.sh: no files under /artifacts" >&2
    exit 1
fi
echo "docker-build-entry.sh: artifacts ready under /artifacts"
