#!/usr/bin/env bash
# Install Python (Poetry) and Node (pnpm) dependencies for native Electron builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/priv.sh
. "$(dirname "$0")/priv.sh"

export GIT_TERMINAL_PROMPT=0

if [[ "$(uname -s)" == "Darwin" ]]; then
    brew install codec2
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
    run_priv apt-get install -y libopus0 libogg0
fi

python -m poetry check --lock
python -m poetry install --no-interaction --no-ansi
python -m poetry run python scripts/patch_lxst_pyogg_ogg_ctypes.py

# Python 3.14 may install miniaudio from sdist; a mis-linked x86_64-only
# _miniaudio.abi3.so in the arm64 cx_Freeze tree differs from the x64 slice and
# breaks @electron/universal (lipo cannot merge two x86_64-only Mach-O files).
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    if ! poetry run python -c "
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
if 'x86_64' in out and 'arm64' not in out:
    sys.exit(1)
sys.exit(0)
"; then
        echo "Rebuilding miniaudio for arm64 (was x86_64-only)." >&2
        (
            export ARCHFLAGS="-arch arm64"
            export CFLAGS="-arch arm64 ${CFLAGS:-}"
            export CXXFLAGS="-arch arm64 ${CXXFLAGS:-}"
            poetry run python -m pip install --force-reinstall --no-cache-dir --no-binary miniaudio "miniaudio>=1.70,<2"
        )
    fi
fi

pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
