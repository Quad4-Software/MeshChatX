#!/usr/bin/env bash
# Prepare a Wine prefix with Windows Python for cx_Freeze cross-builds.
#
# Default install uses the embeddable zip (reliable in Docker/xvfb). Set
# MESHCHATX_WINE_PYTHON_INSTALLER=1 to use the full Windows installer instead.
#
# Env:
#   WINEPREFIX (default: $HOME/.wine)
#   WINEARCH (default: win64)
#   MESHCHATX_WINE_SETUP_DIR  download/workdir for installers (default: cwd)
#   MESHCHATX_WINE_INSTALL_GIT  0|1 (default: 1)
#   MESHCHATX_WINE_INSTALL_REQUIREMENTS  0|1 (default: 1)
#   MESHCHATX_WINE_FORCE  0|1 (default: 0) reinstall even if python works
#   MESHCHATX_WINE_PYTHON_INSTALLER  0|1 (default: 0) use full .exe installer
set -euo pipefail

export WINEDEBUG=-all
export WINEARCH="${WINEARCH:-win64}"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-winemenubuilder.exe=d}"

PYTHON_VERSION="${MESHCHATX_WINE_PYTHON_VERSION:-3.14.4}"
PYTHON_MAJOR_MINOR="$(printf '%s' "$PYTHON_VERSION" | cut -d. -f1-2 | tr -d '.')"
# python3.14 -> tag used in embed _pth filename is python314._pth
PYTHON_PTH="python${PYTHON_MAJOR_MINOR}._pth"

PYTHON_EXE="python-${PYTHON_VERSION}-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_EXE}"
PYTHON_EMBED_ZIP="python-${PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_EMBED_ZIP}"
GET_PIP_URL="https://bootstrap.pypa.io/get-pip.py"

GIT_VERSION="${MESHCHATX_WINE_GIT_VERSION:-2.52.0}"
GIT_EXE="Git-${GIT_VERSION}-64-bit.exe"
GIT_URL="https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/${GIT_EXE}"

INSTALL_GIT="${MESHCHATX_WINE_INSTALL_GIT:-1}"
INSTALL_REQUIREMENTS="${MESHCHATX_WINE_INSTALL_REQUIREMENTS:-1}"
FORCE="${MESHCHATX_WINE_FORCE:-0}"
USE_INSTALLER="${MESHCHATX_WINE_PYTHON_INSTALLER:-0}"

SETUP_DIR="${MESHCHATX_WINE_SETUP_DIR:-}"
if [[ -z "$SETUP_DIR" ]]; then
    SETUP_DIR="$(pwd)"
fi
mkdir -p "$SETUP_DIR"
SETUP_DIR="$(cd "$SETUP_DIR" && pwd)"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

wine_wrap() {
    if command -v xvfb-run >/dev/null 2>&1; then
        WINEDEBUG=-all WINEDLLOVERRIDES="$WINEDLLOVERRIDES" xvfb-run -a "$@"
    else
        WINEDEBUG=-all WINEDLLOVERRIDES="$WINEDLLOVERRIDES" "$@"
    fi
}

wine_python_ok() {
    wine_wrap wine C:/Python314/python.exe --version >/dev/null 2>&1
}

ensure_wine_prefix() {
    if [[ -d "${WINEPREFIX}/drive_c" ]]; then
        return 0
    fi
    echo "Initializing Wine prefix in $WINEPREFIX..."
    wine_wrap wine wineboot --init
    # Let wineserver settle before the next heavy process.
    wine_wrap wineserver -w || true
}

install_python_embed() {
    local extract_dir pth_host wheels_dir
    echo "Downloading embeddable Windows Python ${PYTHON_VERSION}..."
    curl -fsSL --retry 5 --retry-all-errors -o "${SETUP_DIR}/${PYTHON_EMBED_ZIP}" "$PYTHON_EMBED_URL"

    extract_dir="${WINEPREFIX}/drive_c/Python314"
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    unzip -qo "${SETUP_DIR}/${PYTHON_EMBED_ZIP}" -d "$extract_dir"
    rm -f "${SETUP_DIR}/${PYTHON_EMBED_ZIP}"

    pth_host="${extract_dir}/${PYTHON_PTH}"
    if [[ ! -f "$pth_host" ]]; then
        # Fallback: find any python*._pth in the extract dir.
        pth_host="$(find "$extract_dir" -maxdepth 1 -name 'python*._pth' | head -n1 || true)"
    fi
    if [[ -z "$pth_host" || ! -f "$pth_host" ]]; then
        echo "setup_wine_env.sh: missing ${PYTHON_PTH} in embed package" >&2
        exit 1
    fi
    # Enable site-packages so pip works.
    if grep -q '^#import site' "$pth_host"; then
        sed -i 's/^#import site/import site/' "$pth_host"
    elif ! grep -q '^import site' "$pth_host"; then
        printf '\nimport site\n' >>"$pth_host"
    fi

    # cx_Freeze needs stdlib packages as real directories (email, encodings, ...).
    # The embed zip keeps them inside pythonXY.zip which freezers cannot walk.
    local stdlib_zip
    stdlib_zip="$(find "$extract_dir" -maxdepth 1 -name 'python*.zip' | head -n1 || true)"
    if [[ -n "$stdlib_zip" && -f "$stdlib_zip" ]]; then
        echo "Expanding embeddable stdlib zip for cx_Freeze..."
        mkdir -p "${extract_dir}/Lib"
        unzip -qo "$stdlib_zip" -d "${extract_dir}/Lib"
        rm -f "$stdlib_zip"
        # Point ._pth at Lib instead of the removed zip.
        local zip_base
        zip_base="$(basename "$stdlib_zip")"
        if grep -q "^${zip_base}$" "$pth_host"; then
            sed -i "s|^${zip_base}$|Lib|" "$pth_host"
        elif ! grep -q '^Lib$' "$pth_host"; then
            printf 'Lib\n' >>"$pth_host"
        fi
    fi

    # Wine SSL to pypi often fails. Fetch get-pip and wheels with Linux curl/pip,
    # then install offline into Wine Python.
    echo "Bootstrapping pip into embeddable Python (offline wheels)..."
    curl -fsSL --retry 5 --retry-all-errors -o "${SETUP_DIR}/get-pip.py" "$GET_PIP_URL"
    wheels_dir="${SETUP_DIR}/win-bootstrap-wheels"
    rm -rf "$wheels_dir"
    mkdir -p "$wheels_dir"
    # Prefer host pip download. uv pip download is not available on all uv pins.
    if python3 -m pip download --help >/dev/null 2>&1; then
        python3 -m pip download pip setuptools wheel \
            --python-version "${PYTHON_VERSION%.*}" \
            --platform win_amd64 \
            --only-binary=:all: \
            -d "$wheels_dir"
    elif command -v uv >/dev/null 2>&1 && uv pip download --help >/dev/null 2>&1; then
        uv pip download pip setuptools wheel \
            --python-version "${PYTHON_VERSION%.*}" \
            --platform win_amd64 \
            --only-binary=:all: \
            -d "$wheels_dir"
    else
        echo "setup_wine_env.sh: need python3 -m pip download or uv pip download" >&2
        exit 1
    fi
    wine_wrap wine C:/Python314/python.exe "${SETUP_DIR}/get-pip.py" \
        --no-warn-script-location \
        --no-index \
        --find-links "$wheels_dir"
    rm -f "${SETUP_DIR}/get-pip.py"
    rm -rf "$wheels_dir"
}

install_python_exe() {
    echo "Downloading Windows Python installer ${PYTHON_VERSION}..."
    curl -fsSL --retry 5 --retry-all-errors -o "${SETUP_DIR}/${PYTHON_EXE}" "$PYTHON_URL"
    chmod +x "${SETUP_DIR}/${PYTHON_EXE}"
    echo "Installing Python ${PYTHON_VERSION} into Wine (full installer)..."
    wine_wrap wine "${SETUP_DIR}/${PYTHON_EXE}" /quiet InstallAllUsers=1 TargetDir=C:\\Python314 PrependPath=1
    wine_wrap wineserver -w || true
    rm -f "${SETUP_DIR}/${PYTHON_EXE}"
}

if [[ "$FORCE" != "1" ]] && wine_python_ok; then
    echo "Wine Python already present at C:/Python314 (WINEPREFIX=$WINEPREFIX)."
else
    ensure_wine_prefix
    if [[ "$USE_INSTALLER" == "1" ]]; then
        install_python_exe
    else
        install_python_embed
    fi
    if ! wine_python_ok; then
        echo "setup_wine_env.sh: Wine Python failed to start after install" >&2
        exit 1
    fi
fi

if [[ "$INSTALL_GIT" == "1" ]]; then
    if wine_wrap wine "C:/Program Files/Git/cmd/git.exe" --version >/dev/null 2>&1; then
        echo "Git for Windows already present in Wine."
    else
        echo "Downloading Git for Windows ${GIT_VERSION}..."
        curl -fsSL --retry 5 --retry-all-errors -o "${SETUP_DIR}/${GIT_EXE}" "$GIT_URL"
        chmod +x "${SETUP_DIR}/${GIT_EXE}"
        echo "Installing Git into Wine..."
        wine_wrap wine "${SETUP_DIR}/${GIT_EXE}" /VERYSILENT /NORESTART
        wine_wrap wineserver -w || true
        rm -f "${SETUP_DIR}/${GIT_EXE}"
    fi
fi

if [[ "$INSTALL_REQUIREMENTS" == "1" ]]; then
    echo "Installing build dependencies in Wine Python..."
    wine_wrap wine C:/Python314/python.exe -m pip install --upgrade pip
    wine_wrap wine C:/Python314/python.exe -m pip install cx_Freeze
    if [[ -f "${REPO_ROOT}/requirements.txt" ]]; then
        wine_wrap wine C:/Python314/python.exe -m pip install -r "${REPO_ROOT}/requirements.txt"
    fi
else
    echo "Skipping Wine pip requirements (MESHCHATX_WINE_INSTALL_REQUIREMENTS=${INSTALL_REQUIREMENTS})."
fi

echo "Wine setup complete. Example:"
echo "  PLATFORM=win32 PYTHON_CMD='wine C:/Python314/python.exe' pnpm run build-backend"
