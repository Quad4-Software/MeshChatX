#!/usr/bin/env bash
# Run Windows Python under Wine with a PATH that cx_Freeze can read.
# Used by Dockerfile.electron-wine / task docker:dist:win.
set -euo pipefail

export WINEDEBUG="${WINEDEBUG:--all}"
export WINEARCH="${WINEARCH:-win64}"
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-winemenubuilder.exe=d}"
export PATH="${PATH:-/usr/local/bin:/usr/bin:/bin}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-root}"
mkdir -p "$XDG_RUNTIME_DIR"

# Wine maps WINEPATH into the Windows PATH. cx_Freeze 8.x indexes os.environ["PATH"].
export WINEPATH="${WINEPATH:-C:\\Python314;C:\\Python314\\Scripts;C:\\windows\\system32;C:\\windows}"

if command -v xvfb-run >/dev/null 2>&1; then
    exec xvfb-run -a wine C:/Python314/python.exe "$@"
fi
exec wine C:/Python314/python.exe "$@"
