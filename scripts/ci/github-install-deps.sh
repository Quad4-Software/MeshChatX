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

python -m poetry install --no-interaction --no-ansi
pnpm install --frozen-lockfile
