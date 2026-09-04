#!/usr/bin/env bash
# Install locked Python deps for the darwin-x64 cx_Freeze slice on Apple Silicon CI.
# The arm64 slice uses uv sync into .venv. This script mirrors that with .venv-x64 so
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

# Host is arm64. Without --python-platform uv still resolves macOS wheels for aarch64.
# pycodec2 has no cp314 macOS x86_64 wheel, so uv would build it from sdist and pull
# numpy into an isolated cross build (meson: "Can not run test applications").
uv sync --frozen --group dev \
    --python "$PY_X64" \
    --python-platform x86_64-apple-darwin \
    --no-install-package pycodec2

uv pip install --python "$_PY" \
    --python-platform x86_64-apple-darwin \
    "numpy==${_NUMPY_VERSION}"

# pycodec2's sdist imports Cython directly in setup.py but does not declare it
# under build-system.requires, so a build needs it preinstalled in the venv.
# "wheel" registers the bdist_wheel setuptools command used below.
uv pip install --python "$_PY" \
    --python-platform x86_64-apple-darwin \
    "Cython>=3.1.4" wheel

# Host uv is arm64, so "uv pip install --no-build-isolation" would spawn "$_PY"
# (a universal2 binary) with uv's own (arm64) architecture preference. Cython's
# native extension is installed as x86_64-only, so the arm64-loaded interpreter
# fails to dlopen it ("incompatible architecture"). Building the wheel ourselves
# lets us force x86_64 on the one interpreter invocation that runs native code
# (via arch -x86_64), then hand uv a finished wheel to install, which is a
# plain file copy where uv's own architecture no longer matters.
_lock_sdist_url() {
    awk -v pkg="$1" '
        $0 == "name = \"" pkg "\"" { found=1; next }
        found && /^sdist = / { print; exit }
    ' uv.lock | sed -n 's/.*url = "\([^"]*\)".*/\1/p'
}

_PYCODEC2_SDIST_URL="$(_lock_sdist_url pycodec2)"
if [[ -z "$_PYCODEC2_SDIST_URL" ]]; then
    echo "github-install-macos-x64-python-deps: failed to read pycodec2 sdist url from uv.lock" >&2
    exit 1
fi

_pycodec2_build_dir="$(mktemp -d)"
trap 'rm -rf "$_pycodec2_build_dir"' EXIT

curl -fsSL "$_PYCODEC2_SDIST_URL" -o "${_pycodec2_build_dir}/pycodec2.tar.gz"
tar xzf "${_pycodec2_build_dir}/pycodec2.tar.gz" -C "$_pycodec2_build_dir"
_pycodec2_src_dir="$(find "$_pycodec2_build_dir" -maxdepth 1 -type d -name 'pycodec2-*')"
if [[ -z "$_pycodec2_src_dir" ]]; then
    echo "github-install-macos-x64-python-deps: pycodec2 sdist did not extract as expected" >&2
    exit 1
fi

(cd "$_pycodec2_src_dir" && arch -x86_64 "$_PY" setup.py bdist_wheel -d "${_pycodec2_build_dir}/dist")

_pycodec2_wheel="$(find "${_pycodec2_build_dir}/dist" -maxdepth 1 -name 'pycodec2-*.whl')"
if [[ -z "$_pycodec2_wheel" ]]; then
    echo "github-install-macos-x64-python-deps: pycodec2 wheel build produced no output" >&2
    exit 1
fi

uv pip install --python "$_PY" \
    --python-platform x86_64-apple-darwin \
    "$_pycodec2_wheel"

# Cython/wheel are build-time-only tools for the pycodec2 sdist compile above.
# The finished wheel's .so no longer needs them at runtime. uv.lock does not
# pin either, so leaving them installed would make this venv's site-packages
# diverge from .venv's (arm64, which never builds pycodec2 from source and
# never needs them) -- cx_Freeze's module finder bundles whatever is actually
# importable, so an extra build tool sitting in site-packages here can end up
# in lib/library.zip on one slice only, which unify-backend then rejects as a
# genuine module-set mismatch between the two macOS trees.
uv pip uninstall --python "$_PY" Cython wheel

# pycodec2's setup.py links with -lcodec2, so the extension records Homebrew's
# absolute install name for libcodec2 (e.g. /usr/local/opt/codec2/lib/libcodec2.1.2.dylib).
# That only resolves on this CI runner. Bundle the dylib next to the extension and
# rewrite the load command to @loader_path/libcodec2.dylib so it is self-contained,
# and matches the relative layout scripts/unify-backend-plain-files.sh expects when
# reconciling this slice against the arm64 wheel's .dylibs/ bundle.
if [[ -n "${_codec2:-}" ]]; then
    _pycodec2_dir="$(arch -x86_64 "$_PY" -c '
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
    for _lib in "${_codec2}/lib/libcodec2.dylib" "${_codec2}/lib/libcodec2.so"; do
        if [[ -f "$_lib" ]]; then
            cp -f "$_lib" "${_pycodec2_dir}/libcodec2.dylib"
            break
        fi
    done
fi
arch -x86_64 bash "$(dirname "$0")/macos-normalize-pycodec2-dylib.sh" "$_PY"

arch -x86_64 "$_PY" scripts/patch_lxst_pyogg_ogg_ctypes.py
arch -x86_64 "$_PY" scripts/patch_lxst_codec2_optional.py

arch -x86_64 "$_PY" -c "
import importlib.metadata
import numpy
import pycodec2
from numpy._core._multiarray_umath import _add_newdoc_ufunc
print('x64 venv numpy', numpy.__version__, 'pycodec2', importlib.metadata.version('pycodec2'), 'ok')
"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "PYTHON_CMD_X64=${UV_PROJECT_ENVIRONMENT}/bin/python" >>"$GITHUB_ENV"
fi
