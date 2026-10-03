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

_lock_resolved_version() {
    # $1 package, $2 interpreter version (MAJOR.MINOR). uv export emits one
    # requirements line per locked release with its environment marker, so a
    # marker-split pin resolves to the release this interpreter would get.
    uv export --frozen --no-dev --format requirements-txt 2>/dev/null | awk -v pkg="$1" -v py="$2" '
        function cmpver(a, b,   A, B, i) {
            split(a, A, "."); split(b, B, ".")
            for (i = 1; i <= 3; i++) {
                if ((A[i] + 0) != (B[i] + 0)) return (A[i] + 0) > (B[i] + 0) ? 1 : -1
            }
            return 0
        }
        index($0, pkg "==") == 1 {
            ver = $0
            sub("^[^=]*==", "", ver)
            sub(/[ \t].*$/, "", ver)
            marker = ""
            if (index($0, ";") > 0) {
                marker = $0
                sub(/^[^;]*;[ ]*/, "", marker)
                sub(/[ ]*\\[ ]*$/, "", marker)
            }
            if (marker == "") { print ver; exit }
            if (marker ~ /^python_full_version[ ]*[<>=!]/) {
                split(marker, q, "'\''")
                lim = q[2]
                c = cmpver(py, lim)
                ok = 0
                if (marker ~ /^python_full_version[ ]*>=/) ok = (c >= 0)
                else if (marker ~ /^python_full_version[ ]*<=/) ok = (c <= 0)
                else if (marker ~ /^python_full_version[ ]*==/) ok = (c == 0)
                else if (marker ~ /^python_full_version[ ]*!=/) ok = (c != 0)
                else if (marker ~ /^python_full_version[ ]*</) ok = (c < 0)
                else if (marker ~ /^python_full_version[ ]*>/) ok = (c > 0)
                if (ok) { print ver; exit }
            }
        }
    '
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

_PY_MM="$(arch -x86_64 "$_PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
_NUMPY_VERSION="$(_lock_resolved_version numpy "$_PY_MM")"
if [[ -z "$_NUMPY_VERSION" ]]; then
    echo "github-macos-x64-venv-ready: could not resolve numpy from uv.lock" >&2
    _mark false
    exit 0
fi

if ! arch -x86_64 "$_PY" -c "
import importlib.metadata
import numpy
from numpy._core._multiarray_umath import _ARRAY_API
from meshchatx import pycodec2_ctypes

want_numpy = '${_NUMPY_VERSION}'
got_numpy = numpy.__version__
if got_numpy != want_numpy:
    raise SystemExit(f'numpy {got_numpy} != {want_numpy}')
codec = pycodec2_ctypes.Codec2(1600)
if codec.samples_per_frame() <= 0:
    raise SystemExit('codec2 ctypes binding returned no samples')
print('x64 venv ready', got_numpy, 'codec2-ctypes ok')
"; then
    echo "github-macos-x64-venv-ready: cached env incomplete or wrong versions; discarding" >&2
    rm -rf "${UV_PROJECT_ENVIRONMENT}"
    _mark false
    exit 0
fi

_mark true
