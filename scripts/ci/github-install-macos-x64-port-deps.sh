#!/usr/bin/env bash
# Install locked Python deps for the darwin-x64 cx_Freeze slice using MacPorts.
# Intended for the GitHub-hosted macos-15-intel x86_64 runner. Homebrew no longer
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
# opus* / libogg / libvorbis / flac back the pyogg dylib normalization. The
# vendored set already matches x86_64, so this is belt-and-suspenders for
# when upstream LXST changes the bundled arch mix.
sudo port -N install codec2 libyaml openssl libopus opusfile libopusenc libogg libvorbis flac

# sdist builds for cryptography and libcst need a Rust toolchain.
bash "$(dirname "$0")/github-macos-rust-x64-target.sh"
if [[ -f "${HOME}/.cargo/env" ]]; then
    # shellcheck disable=SC1091
    source "${HOME}/.cargo/env"
fi

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

# pycodec2 has no macOS x86_64 wheel and its sdist needs an undeclared
# Cython build. The ctypes binding in meshchatx/pycodec2_ctypes.py covers
# the Codec2 API LXST uses, so this slice skips the extension entirely and
# ships MacPorts libcodec2 for the binding to dlopen.
uv sync --frozen --group dev \
    --python "$PY_X64" \
    --no-install-package pycodec2

# numpy is marker-split per interpreter version, so the lock holds more than
# one release. The sync above already picked the right wheel. Pin that one.
_NUMPY_VERSION="$("$_PY" -c 'import importlib.metadata; print(importlib.metadata.version("numpy"))')"
if [[ -z "$_NUMPY_VERSION" ]]; then
    echo "github-install-macos-x64-port-deps: failed to read installed numpy version" >&2
    exit 1
fi

uv pip install --python "$_PY" \
    "numpy==${_NUMPY_VERSION}"

# Ship the MacPorts libcodec2 at the site-packages root so the ctypes binding
# finds it without the pycodec2 extension. cx_Freeze picks it up from there
# via the include_files entry in cx_setup.py.
_site_packages="$("$_PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
cp -f "/opt/local/lib/libcodec2.dylib" "${_site_packages}/libcodec2.dylib"

bash "$(dirname "$0")/macos-normalize-pyogg-dylibs.sh" "$_PY"

"$_PY" scripts/patch_lxst_pyogg_ogg_ctypes.py
"$_PY" scripts/patch_lxst_codec2_optional.py

"$_PY" -c "
import numpy
from numpy._core._multiarray_umath import _ARRAY_API
from meshchatx import pycodec2_ctypes
codec = pycodec2_ctypes.Codec2(1600)
assert codec.samples_per_frame() > 0
print('x64 venv numpy', numpy.__version__, 'codec2-ctypes ok')
"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "PYTHON_CMD_X64=${_PY}" >> "$GITHUB_ENV"
fi
