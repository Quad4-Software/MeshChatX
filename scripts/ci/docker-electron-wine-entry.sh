#!/usr/bin/env bash
# Run inside Dockerfile.electron-wine (electronuserland/builder + Wine Python).
# Builds Windows Electron portable/NSIS via electron-builder under Wine.
#
# Env:
#   MESHCHATX_ELECTRON_WINE_TARGETS = smoke | win | linux+win (default: win)
#   PNPM_VERSION, UV_VERSION, TASK_VERSION  optional pins
set -euo pipefail

cd /project

export WINEDEBUG=-all
export WINEARCH="${WINEARCH:-win64}"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
export UV_VERSION="${UV_VERSION:-0.11.15}"
export PNPM_VERSION="${PNPM_VERSION:-11.1.2}"
export ELECTRON_CACHE="${ELECTRON_CACHE:-/root/.cache/electron}"
export ELECTRON_BUILDER_CACHE="${ELECTRON_BUILDER_CACHE:-/root/.cache/electron-builder}"

WINE_PYTHON_CMD="${WINE_PYTHON:-/project/scripts/ci/wine-python.sh}"

wine_wrap() {
    if command -v xvfb-run >/dev/null 2>&1; then
        WINEDEBUG=-all xvfb-run -a "$@"
    else
        WINEDEBUG=-all "$@"
    fi
}

run_wine_python() {
    # shellcheck disable=SC2086
    wine_wrap ${WINE_PYTHON_CMD} "$@"
}

ensure_host_tools() {
    if ! command -v curl >/dev/null 2>&1 || ! command -v xvfb-run >/dev/null 2>&1 || ! command -v unzip >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y --no-install-recommends ca-certificates curl xvfb unzip
    fi

    if ! command -v node >/dev/null 2>&1; then
        echo "docker-electron-wine-entry.sh: node missing from base image" >&2
        exit 1
    fi

    if ! command -v wine >/dev/null 2>&1; then
        echo "docker-electron-wine-entry.sh: wine missing from base image" >&2
        exit 1
    fi

    corepack enable
    corepack prepare "pnpm@${PNPM_VERSION}" --activate

    if ! command -v task >/dev/null 2>&1; then
        sh scripts/ci/setup-task.sh "${TASK_VERSION:-3.49.1}"
    fi

    if ! command -v uv >/dev/null 2>&1; then
        bash scripts/ci/github-install-uv.sh
    fi
}

ensure_wine_python() {
    if run_wine_python --version >/dev/null 2>&1; then
        run_wine_python --version
        return 0
    fi
    MESHCHATX_WINE_INSTALL_REQUIREMENTS=0 \
        MESHCHATX_WINE_SETUP_DIR=/tmp/meshchatx-wine-setup \
        bash scripts/setup_wine_env.sh
    run_wine_python --version
}

install_wine_python_deps() {
    # Wine HTTPS to PyPI is unreliable. Download win_amd64 wheels with host pip,
    # then pip install --no-index into Wine Python.
    #
    # uv export includes linux/darwin/win32 marker lines. Host pip evaluates
    # markers for Linux, so filter to win32 and strip markers first.
    echo "Downloading Windows wheels via host pip, installing into Wine Python..."
    local req_tmp req_win wheels_dir
    req_tmp="$(mktemp)"
    req_win="$(mktemp)"
    wheels_dir="$(mktemp -d)"
    uv export --no-dev --no-hashes -o "$req_tmp"
    python3 scripts/ci/filter-requirements-platform.py \
        --sys-platform win32 \
        --python-version 3.14.4 \
        --input "$req_tmp" \
        --output "$req_win"

    # Project deps are pre-filtered for win32. Download without resolving foreign
    # markers. cx_Freeze + freeze-core (and freeze-core's win deps) are fetched
    # explicitly with --no-deps so host pip does not pull Linux-only patchelf.
    python3 -m pip download --no-deps -r "$req_win" \
        --python-version 3.14 \
        --platform win_amd64 \
        --only-binary=:all: \
        -d "$wheels_dir"
    python3 -m pip download --no-deps \
        cx_Freeze freeze-core filelock cabarchive striprtf setuptools wheel \
        --python-version 3.14 \
        --platform win_amd64 \
        --only-binary=:all: \
        -d "$wheels_dir"

    # Offline only. Do not let Wine pip hit PyPI (SSL is broken in this image).
    # The project itself is imported from /project (cwd) during cx_Freeze. Skip
    # pip install . so Wine does not try to fetch build isolation deps from PyPI.
    run_wine_python -m pip install --no-index --find-links "$wheels_dir" --no-deps -r "$req_win"
    run_wine_python -m pip install --no-index --find-links "$wheels_dir" --no-deps \
        setuptools wheel filelock cabarchive striprtf freeze-core cx_Freeze
    # Editable/project install needs setuptools already present (no build isolation,
    # no PyPI). Wine maps /project as Z:\project in this base image.
    run_wine_python -m pip install --no-index --find-links "$wheels_dir" \
        --no-build-isolation --no-deps .
    run_wine_python -c "import cx_Freeze, meshchatx, RNS, LXMF; print('wine python deps ok', cx_Freeze.__version__, meshchatx.__file__)"
    rm -f "$req_tmp" "$req_win"
    rm -rf "$wheels_dir"
}

build_frontend_and_node() {
    export TRIVY_SBOM=0
    pnpm config set verify-store-integrity true
    pnpm install --frozen-lockfile
    # Linux uv sync is still useful for license bake / helper scripts on the host side.
    uv lock --check
    uv sync --group dev
    uv run python scripts/patch_lxst_pyogg_ogg_ctypes.py
    uv run python scripts/patch_lxst_codec2_optional.py
    task build:frontend
    pnpm run electron-postinstall
}

build_win() {
    echo "Building Windows cx_Freeze backend via Wine Python..."
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-root}"
    mkdir -p "$XDG_RUNTIME_DIR"
    PLATFORM=win32 PYTHON_CMD="${WINE_PYTHON_CMD}" pnpm run build-backend

    # cx_Freeze under Wine may still zip stdlib email. Copy the expanded Lib tree
    # so Windows relative email imports and CI verify keep working.
    local win_lib email_src
    win_lib="build/exe/win32-x64/lib"
    email_src="${WINEPREFIX}/drive_c/Python314/Lib/email"
    if [[ -d "$email_src" ]]; then
        mkdir -p "$win_lib"
        rm -rf "${win_lib}/email"
        cp -a "$email_src" "${win_lib}/email"
        echo "Copied stdlib email into ${win_lib}/email"
    fi

    echo "Packaging Windows portable + NSIS with electron-builder..."
    # NSIS under Wine often needs a fake display.
    if command -v xvfb-run >/dev/null 2>&1; then
        xvfb-run -a npx electron-builder --win portable nsis --publish=never
    else
        npx electron-builder --win portable nsis --publish=never
    fi

    bash scripts/ci/github-prune-electron-dist-staging.sh
    bash scripts/ci/github-verify-electron-dist.sh win

    if [[ -d build/exe ]]; then
        bash scripts/ci/github-verify-frozen-sandbox.sh build/exe
        bash scripts/ci/github-verify-frozen-runtime.sh build/exe
        bash scripts/ci/github-verify-frozen-codec2.sh build/exe
        bash scripts/ci/github-verify-frozen-umsgpack.sh build/exe
    fi
}

build_linux() {
    echo "Building Linux Electron packages inside wine image (optional)..."
    PLATFORM=linux pnpm run build-backend
    if command -v xvfb-run >/dev/null 2>&1; then
        xvfb-run -a npx electron-builder --linux AppImage deb --publish=never
    else
        npx electron-builder --linux AppImage deb --publish=never
    fi
    bash scripts/ci/github-prune-electron-dist-staging.sh
}

stage_artifacts() {
    mkdir -p /artifacts
    if [[ -d dist ]]; then
        cp -a dist/. /artifacts/
    fi
    if [[ -z "$(ls -A /artifacts 2>/dev/null || true)" ]]; then
        if [[ "${MESHCHATX_ELECTRON_WINE_TARGETS:-win}" == "smoke" ]]; then
            printf 'smoke ok\n' >/artifacts/SMOKE_OK.txt
        else
            echo "docker-electron-wine-entry.sh: no files under /artifacts" >&2
            exit 1
        fi
    fi
    echo "docker-electron-wine-entry.sh: artifacts ready under /artifacts"
    ls -la /artifacts | head -40 || true
}

targets="${MESHCHATX_ELECTRON_WINE_TARGETS:-win}"
ensure_host_tools
ensure_wine_python

case "$targets" in
    smoke)
        echo "Smoke target: toolchain only (node/wine/python)."
        node --version
        pnpm --version
        wine --version
        run_wine_python --version
        ;;
    win)
        install_wine_python_deps
        build_frontend_and_node
        build_win
        ;;
    linux+win|all)
        install_wine_python_deps
        build_frontend_and_node
        build_linux
        build_win
        ;;
    *)
        echo "Unknown MESHCHATX_ELECTRON_WINE_TARGETS=${targets} (use smoke|win|linux+win)" >&2
        exit 1
        ;;
esac

stage_artifacts
