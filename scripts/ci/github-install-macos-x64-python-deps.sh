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

# Host is arm64; without --python-platform uv still resolves macOS wheels for aarch64.
uv sync --frozen --group dev --python "$PY_X64" --python-platform x86_64-apple-darwin
arch -x86_64 "${UV_PROJECT_ENVIRONMENT}/bin/python" scripts/patch_lxst_pyogg_ogg_ctypes.py

arch -x86_64 "${UV_PROJECT_ENVIRONMENT}/bin/python" -c "
import numpy
from numpy._core._multiarray_umath import _add_newdoc_ufunc
print('x64 venv numpy', numpy.__version__, 'ok')
"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "PYTHON_CMD_X64=${UV_PROJECT_ENVIRONMENT}/bin/python" >>"$GITHUB_ENV"
fi
