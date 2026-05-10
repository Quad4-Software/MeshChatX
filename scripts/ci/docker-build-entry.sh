#!/usr/bin/env bash
# Run inside Dockerfile.build after COPY. Writes outputs to /artifacts.
# Env: MESHCHATX_BUILD_TARGETS = all | wheel | electron (electron = AppImage+deb per arch + best-effort RPM, no wheel)
set -euo pipefail

cd /src

export POETRY_VERSION="${POETRY_VERSION:-2.3.4}"
export PNPM_VERSION="${PNPM_VERSION:-10.33.0}"

apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates curl git jq unzip xz-utils \
    build-essential pkg-config python3-dev

install_electron_builder_libs() {
    apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 libasound2 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxkbcommon0 \
        libfuse2 zstd libgtk-3-0
}

if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
    apt-get install -y nodejs
fi

TASK_VER="${TASK_VERSION:-3.46.4}"
_TASK_ARCH="$(uname -m)"
case "$_TASK_ARCH" in
    x86_64) _TASK_ARCH="amd64" ;;
    aarch64) _TASK_ARCH="arm64" ;;
esac
curl -fsSL "https://github.com/go-task/task/releases/download/v${TASK_VER}/task_linux_${_TASK_ARCH}.tar.gz" \
    | tar xz -C /usr/local/bin task

corepack enable
corepack prepare "pnpm@${PNPM_VERSION}" --activate

bash scripts/ci/github-install-poetry.sh

export TRIVY_SBOM=0

targets="${MESHCHATX_BUILD_TARGETS:-all}"
case "$targets" in
    wheel)
        bash scripts/ci/github-install-deps.sh
        export SKIP_ELECTRON=1
        bash scripts/ci/github-build-linux-release-assets.sh
        ;;
    electron)
        install_electron_builder_libs
        bash scripts/ci/github-apt-linux-packaging.sh
        bash scripts/ci/github-install-deps.sh
        task build:fe
        export SKIP_WHEEL=1
        bash scripts/ci/github-build-linux-release-assets.sh
        ;;
    all|*)
        install_electron_builder_libs
        bash scripts/ci/github-apt-linux-packaging.sh
        bash scripts/ci/github-install-deps.sh
        task build:fe
        export SKIP_WHEEL=0
        export SKIP_ELECTRON=0
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
