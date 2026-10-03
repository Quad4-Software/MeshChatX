#!/usr/bin/env bash
# Install locked Python deps for the darwin-x64 cx_Freeze slice on Apple Silicon CI.
# The arm64 slice uses uv sync into .venv. This script mirrors that with .venv-x64 so
# NumPy/LXST native wheels match the lockfile instead of unpinned pip -e . resolution.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "github-install-macos-x64-python-deps: skipping (not macOS)" >&2
    exit 0
fi

export UV_PROJECT_ENVIRONMENT="${ROOT}/.venv-x64"
export UV_PYTHON_INSTALL_DIR="${ROOT}/.cache/uv/python"

uv lock --check

# Warm CI cache: reuse .venv-x64 when numpy/pycodec2 already match uv.lock.
_ready_out="$(mktemp)"
GITHUB_OUTPUT="$_ready_out" bash "$(dirname "$0")/github-macos-x64-venv-ready.sh"
_ready="$(grep -E '^ready=' "$_ready_out" | tail -n1 | cut -d= -f2 || true)"
rm -f "$_ready_out"
if [[ "$_ready" == "true" ]]; then
    echo "github-install-macos-x64-python-deps: warm .venv-x64 reused (skip rebuild)" >&2
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        echo "PYTHON_CMD_X64=${UV_PROJECT_ENVIRONMENT}/bin/python" >>"$GITHUB_ENV"
    fi
    exit 0
fi

PY_X64="${PY_X64:?PY_X64 must point at an x86_64 Python 3.14 interpreter}"

# cryptography 49+ ships arm64-only macOS wheels, so the x64 slice builds from
# sdist and needs a usable x86_64 OpenSSL. brew --prefix can still resolve when
# the cellar path is a broken symlink, so require lib/ and include/ before export.
_openssl_usable_prefix() {
    local prefix="${1:-}"
    if [[ -n "$prefix" && -d "${prefix}/lib" && -d "${prefix}/include" ]]; then
        printf '%s\n' "$prefix"
        return 0
    fi
    return 1
}

_openssl=""
if [[ -x /usr/local/bin/brew ]]; then
    _openssl="$(_openssl_usable_prefix "$(arch -x86_64 /usr/local/bin/brew --prefix openssl@3 2>/dev/null || true)" || true)"
    if [[ -z "$_openssl" ]]; then
        echo "github-install-macos-x64-python-deps: installing openssl@3 for x64 cryptography sdist" >&2
        if ! arch -x86_64 /usr/local/bin/brew install --build-from-source openssl@3; then
            arch -x86_64 /usr/local/bin/brew reinstall --build-from-source openssl@3 || true
        fi
        _openssl="$(_openssl_usable_prefix "$(arch -x86_64 /usr/local/bin/brew --prefix openssl@3 2>/dev/null || true)" || true)"
    fi
fi

_codec2="$(arch -x86_64 /usr/local/bin/brew --prefix codec2 2>/dev/null || true)"
if [[ -z "$_codec2" ]]; then
    echo "github-install-macos-x64-python-deps: installing codec2 for x64 ctypes binding" >&2
    arch -x86_64 /usr/local/bin/brew install codec2
    _codec2="$(arch -x86_64 /usr/local/bin/brew --prefix codec2 2>/dev/null || true)"
fi
if [[ -n "$_codec2" && -d "${_codec2}/include" ]]; then
    export LDFLAGS="${LDFLAGS:-} -L${_codec2}/lib -arch x86_64"
    export CPPFLAGS="${CPPFLAGS:-} -I${_codec2}/include -arch x86_64"
    export PKG_CONFIG_PATH="${_codec2}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
fi

# Never export OPENSSL_* at a missing path. openssl-sys panics on that.
unset OPENSSL_DIR OPENSSL_LIB_DIR OPENSSL_INCLUDE_DIR || true
if [[ -n "$_openssl" ]]; then
    export LDFLAGS="${LDFLAGS:-} -L${_openssl}/lib -arch x86_64"
    export CPPFLAGS="${CPPFLAGS:-} -I${_openssl}/include -arch x86_64"
    export PKG_CONFIG_PATH="${_openssl}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    export OPENSSL_DIR="${_openssl}"
    export OPENSSL_LIB_DIR="${_openssl}/lib"
    export OPENSSL_INCLUDE_DIR="${_openssl}/include"
else
    echo "github-install-macos-x64-python-deps: usable openssl@3 x64 missing, cryptography sdist may fail" >&2
fi

export ARCHFLAGS="${ARCHFLAGS:--arch x86_64}"
export CC="${CC:-clang -arch x86_64}"
export CXX="${CXX:-clang++ -arch x86_64}"
export CFLAGS="${CFLAGS:--arch x86_64}"

_PY="${UV_PROJECT_ENVIRONMENT}/bin/python"

# Host is arm64. Without --python-platform uv still resolves macOS wheels for aarch64.
# pycodec2 has no cp314 macOS x86_64 wheel, and its sdist needs an undeclared
# Cython build. The ctypes binding in meshchatx/pycodec2_ctypes.py covers
# the Codec2 API LXST uses, so this slice skips the extension and ships the
# Homebrew libcodec2 for the binding to dlopen.
uv sync --frozen --group dev \
    --python "$PY_X64" \
    --python-platform x86_64-apple-darwin \
    --no-install-package pycodec2

# numpy is marker-split per interpreter version, so the lock holds more than
# one release. The sync above already picked the right wheel; pin that one.
_NUMPY_VERSION="$("$_PY" -c 'import importlib.metadata; print(importlib.metadata.version("numpy"))')"
if [[ -z "$_NUMPY_VERSION" ]]; then
    echo "github-install-macos-x64-python-deps: failed to read installed numpy version" >&2
    exit 1
fi

uv pip install --python "$_PY" \
    --python-platform x86_64-apple-darwin \
    "numpy==${_NUMPY_VERSION}"

# Ship the Homebrew libcodec2 at the site-packages root so the ctypes
# binding finds it without the pycodec2 extension. cx_Freeze picks it up
# from there via the include_files entry in cx_setup.py.
if [[ -n "${_codec2:-}" ]]; then
    _site_packages="$(arch -x86_64 "$_PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
    for _lib in "${_codec2}/lib/libcodec2.dylib" "${_codec2}/lib/libcodec2.so"; do
        if [[ -f "$_lib" ]]; then
            cp -f "$_lib" "${_site_packages}/libcodec2.dylib"
            break
        fi
    done
fi

arch -x86_64 "$_PY" scripts/patch_lxst_pyogg_ogg_ctypes.py
arch -x86_64 "$_PY" scripts/patch_lxst_codec2_optional.py

arch -x86_64 "$_PY" -c "
import numpy
from numpy._core._multiarray_umath import _ARRAY_API
from meshchatx import pycodec2_ctypes
codec = pycodec2_ctypes.Codec2(1600)
assert codec.samples_per_frame() > 0
print('x64 venv numpy', numpy.__version__, 'codec2-ctypes ok')
"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "PYTHON_CMD_X64=${UV_PROJECT_ENVIRONMENT}/bin/python" >>"$GITHUB_ENV"
fi
