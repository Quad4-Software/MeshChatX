#!/usr/bin/env bash
# Report whether .venv-x64 is ready for the macOS universal cx_Freeze slice.
#
# Exit 0 always. When usable, prints ready=true and exports PYTHON_CMD_X64 to
# GITHUB_ENV / GITHUB_OUTPUT when those files are set.
#
# Env:
#   UV_PROJECT_ENVIRONMENT  default: $ROOT/.venv-x64
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "ready=false" >>"$GITHUB_OUTPUT"
    fi
    exit 0
fi

export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-${ROOT}/.venv-x64}"
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

_mark() {
    local ready="$1"
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "ready=${ready}" >>"$GITHUB_OUTPUT"
    fi
    if [[ "$ready" == "true" ]]; then
        echo "github-macos-x64-venv-ready: reusing ${UV_PROJECT_ENVIRONMENT}" >&2
        if [[ -n "${GITHUB_ENV:-}" ]]; then
            echo "PYTHON_CMD_X64=${_PY}" >>"$GITHUB_ENV"
        fi
    fi
}

if [[ ! -x "$_PY" ]]; then
    _mark false
    exit 0
fi

_NUMPY_VERSION="$(_lock_version numpy)"
_PYCODEC2_VERSION="$(_lock_version pycodec2)"
if [[ -z "$_NUMPY_VERSION" || -z "$_PYCODEC2_VERSION" ]]; then
    echo "github-macos-x64-venv-ready: could not read numpy/pycodec2 from uv.lock" >&2
    _mark false
    exit 0
fi

if ! arch -x86_64 "$_PY" -c "
import importlib.metadata
import numpy
import pycodec2
from numpy._core._multiarray_umath import _add_newdoc_ufunc

want_numpy = '${_NUMPY_VERSION}'
want_pycodec2 = '${_PYCODEC2_VERSION}'
got_numpy = numpy.__version__
got_pycodec2 = importlib.metadata.version('pycodec2')
if got_numpy != want_numpy:
    raise SystemExit(f'numpy {got_numpy} != {want_numpy}')
if got_pycodec2 != want_pycodec2:
    raise SystemExit(f'pycodec2 {got_pycodec2} != {want_pycodec2}')
print('x64 venv ready', got_numpy, got_pycodec2)
"; then
    echo "github-macos-x64-venv-ready: cached env incomplete or wrong versions; discarding" >&2
    rm -rf "${UV_PROJECT_ENVIRONMENT}"
    _mark false
    exit 0
fi

_mark true
