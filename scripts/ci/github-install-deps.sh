#!/usr/bin/env bash
# Install Python (UV) and Node (pnpm) dependencies for native Electron builds.
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

uv lock --check
uv sync --group dev
uv run python scripts/patch_lxst_pyogg_ogg_ctypes.py

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

pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
