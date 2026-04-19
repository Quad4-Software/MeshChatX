#!/usr/bin/env bash
# Install Python (Poetry) and Node (pnpm) dependencies for native Electron builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export GIT_TERMINAL_PROMPT=0

# pycodec2 builds against libcodec2. Export for this step and persist to GITHUB_ENV so
# later steps (e.g. pip install -e . for the x64 universal slice) see the same flags.
if [[ "$(uname -s)" == "Darwin" ]]; then
    brew install codec2
    _codec2_prefix="$(brew --prefix codec2)"
    export CPPFLAGS="${CPPFLAGS:-} -I${_codec2_prefix}/include"
    export LDFLAGS="${LDFLAGS:-} -L${_codec2_prefix}/lib"
    if [[ -d "${_codec2_prefix}/lib/pkgconfig" ]]; then
        export PKG_CONFIG_PATH="${_codec2_prefix}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    fi
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        {
            echo "CPPFLAGS=${CPPFLAGS}"
            echo "LDFLAGS=${LDFLAGS}"
            echo "PKG_CONFIG_PATH=${PKG_CONFIG_PATH:-}"
        } >> "$GITHUB_ENV"
    fi
fi

# LXST/pyogg loads libopus (and libogg for Ogg muxing) at runtime. GitHub-hosted
# Linux runners do not ship these by default, so backend Opus encode tests fail
# with PyOggError until the shared libraries are present.
if [[ "$(uname -s)" == "Linux" ]] && command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y libopus0 libogg0
fi

python -m poetry check --lock
python -m poetry install --no-interaction --no-ansi

pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
