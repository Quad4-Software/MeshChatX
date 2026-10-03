#!/usr/bin/env bash
# Install Python (UV) and/or Node (pnpm) dependencies for CI and native builds.
#
# Env (default true):
#   MESHCHATX_INSTALL_PYTHON  sync the project virtualenv and system libs it needs
#   MESHCHATX_INSTALL_NODE    pnpm install --frozen-lockfile
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/priv.sh
. "$(dirname "$0")/priv.sh"

export GIT_TERMINAL_PROMPT=0

INSTALL_PYTHON="${MESHCHATX_INSTALL_PYTHON:-true}"
INSTALL_NODE="${MESHCHATX_INSTALL_NODE:-true}"

if [[ "$INSTALL_PYTHON" == "true" ]]; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        brew install codec2
        # LXST vendored pyogg ships x86_64-only macOS dylibs. The arm64
        # freeze needs native builds, which macos-normalize-pyogg-dylibs.sh
        # copies in from these formulas.
        brew install opus opusfile libopusenc libogg libvorbis flac
        _codec2_prefix="$(brew --prefix codec2)"
        export CPPFLAGS="${CPPFLAGS:-} -I${_codec2_prefix}/include"
        export LDFLAGS="${LDFLAGS:-} -L${_codec2_prefix}/lib"
        if [[ -d "${_codec2_prefix}/lib/pkgconfig" ]]; then
            export PKG_CONFIG_PATH="${_codec2_prefix}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
        fi
    fi

    # LXST/pyogg loads libopus (and libogg for Ogg muxing) at runtime. GitHub-hosted
    # Linux runners do not ship these by default, so backend Opus encode tests fail
    # with PyOggError until the shared libraries are present.
    if [[ "$(uname -s)" == "Linux" ]] && command -v apt-get >/dev/null 2>&1; then
        run_priv apt-get update -y
        run_priv apt-get install -y libopus0 libogg0 libcodec2-dev
    fi

    uv lock --check
    if [[ "$(uname -s)" == "Darwin" ]]; then
        # The ctypes binding in meshchatx/pycodec2_ctypes.py covers the
        # Codec2 API LXST uses, so macOS slices skip the pycodec2
        # extension and ship the Homebrew libcodec2 for it to dlopen.
        uv sync --group dev --no-install-package pycodec2
    else
        uv sync --group dev
    fi
    uv run python scripts/patch_lxst_pyogg_ogg_ctypes.py
    uv run python scripts/patch_lxst_codec2_optional.py

    # LXST ships prebuilt filterlib blobs per CPython ABI. On pre-release
    # interpreters (3.15 beta legs) none exists, so build it from the bundled
    # Filters.c. Exit 2 (no compiler) is non-fatal: LXST compiles via cffi at
    # runtime instead.
    uv run python scripts/build-lxst-filterlib.py || rc=$?
    if [[ "${rc:-0}" == "2" ]]; then
        echo "::warning::no C compiler for LXST filterlib; cffi runtime fallback will compile it"
    elif [[ "${rc:-0}" != "0" ]]; then
        exit "${rc}"
    fi

    if [[ "$(uname -s)" == "Darwin" ]]; then
        # Ship libcodec2 at the site-packages root, matching the darwin-x64
        # slice, so the ctypes binding finds it and the two trees merge
        # cleanly under scripts/unify-backend-plain-files.sh.
        _site_packages="$(uv run python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
        cp -f "${_codec2_prefix}/lib/libcodec2.dylib" "${_site_packages}/libcodec2.dylib"
        uv run python -c "
import numpy
from numpy._core._multiarray_umath import _ARRAY_API
from meshchatx import pycodec2_ctypes
codec = pycodec2_ctypes.Codec2(1600)
assert codec.samples_per_frame() > 0
print('arm64 venv numpy', numpy.__version__, 'codec2-ctypes ok')
"
        bash "$(dirname "$0")/macos-normalize-pyogg-dylibs.sh" "${ROOT}/.venv/bin/python"
    fi

    if [[ "$(uname -s)" == "Darwin" ]]; then
        if uv run python -c "import platform, sys; sys.exit(0 if platform.machine() == 'arm64' else 1)"; then
            _miniaudio_state="$(uv run python -c "
import importlib.util
import pathlib
import subprocess
import sys

spec = importlib.util.find_spec('miniaudio')
if not spec or not spec.origin:
    print('missing')
    sys.exit(0)
so = pathlib.Path(spec.origin).resolve().parent / '_miniaudio.abi3.so'
if not so.is_file():
    print('missing')
    sys.exit(0)
out = subprocess.check_output(['file', str(so)], text=True)
has_arm = 'arm64' in out
has_x86 = 'x86_64' in out
if not has_arm and has_x86:
    print('x86only')
elif has_arm and has_x86:
    print('universal')
elif has_arm and not has_x86:
    print('arm64only')
else:
    print('unknown')
" 2>/dev/null || echo "missing")"
            case "$_miniaudio_state" in
                x86only)
                    echo "miniaudio _miniaudio.abi3.so is x86_64-only on arm64 venv; rebuilding from source." >&2
                    _need_rebuild=1
                    ;;
                universal)
                    echo "miniaudio _miniaudio.abi3.so is universal2; rebuilding as arm64-only so @electron/universal can lipo with the x64 slice." >&2
                    _need_rebuild=1
                    ;;
                *)
                    _need_rebuild=0
                    ;;
            esac
            if [[ "${_need_rebuild:-0}" == "1" ]]; then
                (
                    export ARCHFLAGS="-arch arm64"
                    export CFLAGS="-arch arm64"
                    export CXXFLAGS="-arch arm64"
                    uv run python -m pip install --force-reinstall --no-cache-dir --no-binary miniaudio "miniaudio>=1.70,<2"
                )
            fi
            if ! uv run python -c "
import importlib.util
import pathlib
import subprocess
import sys

spec = importlib.util.find_spec('miniaudio')
if not spec or not spec.origin:
    sys.exit(0)
so = pathlib.Path(spec.origin).resolve().parent / '_miniaudio.abi3.so'
if not so.is_file():
    sys.exit(0)
out = subprocess.check_output(['file', str(so)], text=True)
if 'arm64' not in out:
    sys.stderr.write(out)
    sys.exit(1)
sys.exit(0)
"; then
                if [[ "${MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO:-0}" == "1" ]]; then
                    echo "miniaudio native extension is not arm64-capable, but MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO=1 is set; continuing (the build will drop _miniaudio.abi3.so before lipo)." >&2
                else
                    echo "miniaudio native extension is not arm64-capable; universal macOS builds will fail at lipo." >&2
                    echo "Re-run with MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO=1 to drop optional audio decoding for the DMG." >&2
                    exit 1
                fi
            fi
        fi
    fi
fi

if [[ "$INSTALL_NODE" == "true" ]]; then
    pnpm config set verify-store-integrity true
    pnpm install --frozen-lockfile
fi

if [[ "$INSTALL_PYTHON" != "true" && "$INSTALL_NODE" != "true" ]]; then
    echo "github-install-deps.sh: nothing to install (both MESHCHATX_INSTALL_PYTHON and MESHCHATX_INSTALL_NODE are false)" >&2
    exit 1
fi
