#!/usr/bin/env bash
# Install locked Python deps for the darwin-x64 cx_Freeze slice using MacPorts.
# Intended for the GitHub-hosted macos-15-intel x86_64 runner; Homebrew no longer
# supports Intel macOS, so codec2, openssl, and libyaml come from MacPorts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "github-install-macos-x64-port-deps: skipping (not macOS)" >&2
    exit 0
fi

if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "github-install-macos-x64-port-deps: must run on a native x86_64 macOS runner" >&2
    exit 1
fi

export PATH="/opt/local/bin:/opt/local/sbin:$PATH"

if ! command -v port >/dev/null 2>&1; then
    echo "github-install-macos-x64-port-deps: installing MacPorts" >&2
    _mpkg="MacPorts-2.11.5-15-Sequoia.pkg"
    _murl="https://github.com/macports/macports-base/releases/download/v2.11.5/${_mpkg}"
    curl -fsSL --http1.1 --retry 4 --retry-delay 4 --max-time 120 "$_murl" -o "/tmp/${_mpkg}"
    sudo installer -pkg "/tmp/${_mpkg}" -target /
    rm -f "/tmp/${_mpkg}"
    sudo port -N selfupdate
fi

echo "github-install-macos-x64-port-deps: installing MacPorts deps" >&2
sudo port -N install codec2 libyaml openssl

export UV_PROJECT_ENVIRONMENT="${ROOT}/.venv-x64"
export UV_PYTHON_INSTALL_DIR="${ROOT}/.cache/uv/python"

uv lock --check

PY_X64="${PY_X64:-$(command -v python3 || true)}"
if [[ -z "$PY_X64" || ! -x "$PY_X64" ]]; then
    echo "PY_X64 must point at an x86_64 Python 3.14 interpreter" >&2
    exit 1
fi

export LDFLAGS="-L/opt/local/lib -arch x86_64"
export CPPFLAGS="-I/opt/local/include -arch x86_64"
export PKG_CONFIG_PATH="/opt/local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export OPENSSL_DIR="/opt/local"
export OPENSSL_LIB_DIR="/opt/local/lib"
export OPENSSL_INCLUDE_DIR="/opt/local/include"
export ARCHFLAGS="-arch x86_64"
export CC="clang -arch x86_64"
export CXX="clang++ -arch x86_64"
export CFLAGS="-arch x86_64"

_PY="${UV_PROJECT_ENVIRONMENT}/bin/python"

_lock_version() {
    awk -v pkg="$1" '
        $0 == "name = \"" pkg "\"" { found=1; next }
        found && /^version = / {
            sub(/^version = "/, "", $0)
            sub(/"$/, "", $0)
            print $0
            exit
        }
    ' uv.lock
}

_lock_sdist_url() {
    awk -v pkg="$1" '
        $0 == "name = \"" pkg "\"" { found=1; next }
        found && /^sdist = / { print; exit }
    ' uv.lock | sed -n 's/.*url = "\([^"]*\)".*/\1/p'
}

_NUMPY_VERSION="$(_lock_version numpy)"
_PYCODEC2_VERSION="$(_lock_version pycodec2)"
if [[ -z "$_NUMPY_VERSION" || -z "$_PYCODEC2_VERSION" ]]; then
    echo "github-install-macos-x64-port-deps: failed to read numpy/pycodec2 versions from uv.lock" >&2
    exit 1
fi

uv sync --frozen --group dev \
    --python "$PY_X64" \
    --no-install-package pycodec2

uv pip install --python "$_PY" \
    "numpy==${_NUMPY_VERSION}"

# pycodec2's sdist imports Cython directly in setup.py but does not declare it
# under build-system.requires, so a build needs it preinstalled in the venv.
uv pip install --python "$_PY" \
    "Cython>=3.1.4" wheel

_PYCODEC2_SDIST_URL="$(_lock_sdist_url pycodec2)"
if [[ -z "$_PYCODEC2_SDIST_URL" ]]; then
    echo "github-install-macos-x64-port-deps: failed to read pycodec2 sdist url from uv.lock" >&2
    exit 1
fi

_pycodec2_build_dir="$(mktemp -d)"
trap 'rm -rf "$_pycodec2_build_dir"' EXIT

curl -fsSL --http1.1 --retry 4 --retry-delay 4 --max-time 120 "$_PYCODEC2_SDIST_URL" -o "${_pycodec2_build_dir}/pycodec2.tar.gz"
tar xzf "${_pycodec2_build_dir}/pycodec2.tar.gz" -C "$_pycodec2_build_dir"
_pycodec2_src_dir="$(find "$_pycodec2_build_dir" -maxdepth 1 -type d -name 'pycodec2-*' | head -n1)"
if [[ -z "$_pycodec2_src_dir" ]]; then
    echo "github-install-macos-x64-port-deps: pycodec2 sdist did not extract as expected" >&2
    exit 1
fi

(cd "$_pycodec2_src_dir" && "$_PY" setup.py bdist_wheel -d "${_pycodec2_build_dir}/dist")

_pycodec2_wheel="$(find "${_pycodec2_build_dir}/dist" -maxdepth 1 -name 'pycodec2-*.whl' | head -n1)"
if [[ -z "$_pycodec2_wheel" ]]; then
    echo "github-install-macos-x64-port-deps: pycodec2 wheel build produced no output" >&2
    exit 1
fi

uv pip install --python "$_PY" \
    "$_pycodec2_wheel"

# Cython/wheel were build-time-only tools.
uv pip uninstall --python "$_PY" Cython wheel

# Bundle libcodec2 next to the extension and rewrite the load command so it is
# self-contained. macos-normalize-pycodec2-dylib.sh then finalizes the layout.
_pycodec2_dir="$("$_PY" -c '
import importlib.metadata
from pathlib import Path
dist = importlib.metadata.distribution("pycodec2")
for rel in dist.files or ():
    if rel.parts and rel.parts[0] == "pycodec2":
        located = Path(dist.locate_file(rel))
        if located.parent.name == "pycodec2":
            print(located.parent.resolve())
            break
')"
if [[ -n "$_pycodec2_dir" && -f "/opt/local/lib/libcodec2.dylib" ]]; then
    cp -f "/opt/local/lib/libcodec2.dylib" "${_pycodec2_dir}/libcodec2.dylib"
fi

bash "$(dirname "$0")/macos-normalize-pycodec2-dylib.sh" "$_PY"

"$_PY" scripts/patch_lxst_pyogg_ogg_ctypes.py
"$_PY" scripts/patch_lxst_codec2_optional.py

"$_PY" -c "
import importlib.metadata
import numpy
import pycodec2
from numpy._core._multiarray_umath import _add_newdoc_ufunc
print('x64 venv numpy', numpy.__version__, 'pycodec2', importlib.metadata.version('pycodec2'), 'ok')
"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "PYTHON_CMD_X64=${_PY}" >> "$GITHUB_ENV"
fi
