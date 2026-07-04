#!/usr/bin/env bash
# Install locked Python deps for the darwin-x64 cx_Freeze slice on Apple Silicon CI.
# The arm64 slice uses uv sync into .venv; this script mirrors that with .venv-x64 so
# NumPy/LXST native wheels match the lockfile instead of unpinned pip -e . resolution.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PY_X64="${PY_X64:?PY_X64 must point at an x86_64 Python 3.14 interpreter}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "github-install-macos-x64-python-deps: skipping (not macOS)" >&2
    exit 0
fi

export UV_PROJECT_ENVIRONMENT="${ROOT}/.venv-x64"
export UV_PYTHON_INSTALL_DIR="${ROOT}/.cache/uv/python"

uv lock --check

if [[ -x /usr/local/bin/brew ]]; then
    arch -x86_64 /usr/local/bin/brew install openssl@3
fi

_codec2="$(arch -x86_64 /usr/local/bin/brew --prefix codec2 2>/dev/null || true)"
if [[ -n "$_codec2" && -d "${_codec2}/include" ]]; then
    export LDFLAGS="${LDFLAGS:-} -L${_codec2}/lib -arch x86_64"
    export CPPFLAGS="${CPPFLAGS:-} -I${_codec2}/include -arch x86_64"
    export PKG_CONFIG_PATH="${_codec2}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
fi

if arch -x86_64 /usr/local/bin/brew --prefix openssl@3 >/dev/null 2>&1; then
    _openssl="$(arch -x86_64 /usr/local/bin/brew --prefix openssl@3)"
    export LDFLAGS="${LDFLAGS:-} -L${_openssl}/lib -arch x86_64"
    export CPPFLAGS="${CPPFLAGS:-} -I${_openssl}/include -arch x86_64"
    export PKG_CONFIG_PATH="${_openssl}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    export OPENSSL_DIR="${_openssl}"
    export OPENSSL_LIB_DIR="${_openssl}/lib"
    export OPENSSL_INCLUDE_DIR="${_openssl}/include"
fi

export ARCHFLAGS="${ARCHFLAGS:--arch x86_64}"
export CC="${CC:-clang -arch x86_64}"
export CXX="${CXX:-clang++ -arch x86_64}"
export CFLAGS="${CFLAGS:--arch x86_64}"

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

_NUMPY_VERSION="$(_lock_version numpy)"
_PYCODEC2_VERSION="$(_lock_version pycodec2)"
if [[ -z "$_NUMPY_VERSION" || -z "$_PYCODEC2_VERSION" ]]; then
    echo "github-install-macos-x64-python-deps: failed to read numpy/pycodec2 versions from uv.lock" >&2
    exit 1
fi

# Host is arm64; without --python-platform uv still resolves macOS wheels for aarch64.
# pycodec2 has no cp314 macOS x86_64 wheel, so uv would build it from sdist and pull
# numpy into an isolated cross build (meson: "Can not run test applications").
uv sync --frozen --group dev \
    --python "$PY_X64" \
    --python-platform x86_64-apple-darwin \
    --no-install-package pycodec2

uv pip install --python "$_PY" \
    --python-platform x86_64-apple-darwin \
    "numpy==${_NUMPY_VERSION}"

arch -x86_64 uv pip install --python "$_PY" \
    --no-build-isolation \
    "pycodec2==${_PYCODEC2_VERSION}"

if [[ -n "${_codec2:-}" ]]; then
    _pycodec2_dir="$(arch -x86_64 "$_PY" -c 'import pathlib, pycodec2; print(pathlib.Path(pycodec2.__file__).resolve().parent)')"
    for _lib in "${_codec2}/lib/libcodec2.dylib" "${_codec2}/lib/libcodec2.so"; do
        if [[ -f "$_lib" ]]; then
            cp -f "$_lib" "${_pycodec2_dir}/libcodec2.so"
            if [[ "$_lib" == *.dylib ]]; then
                cp -f "$_lib" "${_pycodec2_dir}/libcodec2.dylib"
            fi
            break
        fi
    done
fi

arch -x86_64 "$_PY" scripts/patch_lxst_pyogg_ogg_ctypes.py

arch -x86_64 "$_PY" -c "
import numpy
import pycodec2
from numpy._core._multiarray_umath import _add_newdoc_ufunc
print('x64 venv numpy', numpy.__version__, 'pycodec2', pycodec2.__version__, 'ok')
"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "PYTHON_CMD_X64=${UV_PROJECT_ENVIRONMENT}/bin/python" >>"$GITHUB_ENV"
fi
