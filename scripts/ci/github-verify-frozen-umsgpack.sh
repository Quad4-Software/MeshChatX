#!/usr/bin/env bash
# Verify cx_Freeze bundled RNS.vendor.umsgpack for LXMF/RNS ratchet persistence.
# Bare "import umsgpack" is not a project dependency; the freeze must ship the
# vendored module under RNS.vendor (GitHub issue 76).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_EXE="${1:-${ROOT}/build/exe}"

if [[ ! -d "${BUILD_EXE}" ]]; then
    echo "cx_Freeze output not found at ${BUILD_EXE}" >&2
    exit 1
fi

if [[ ! -d "${BUILD_EXE}/lib" ]]; then
    for sub in "${BUILD_EXE}"/*; do
        if [[ -d "${sub}/lib" ]]; then
            BUILD_EXE="${sub}"
            break
        fi
    done
fi

LIB_DIR="${BUILD_EXE}/lib"
LIBRARY_ZIP="${LIB_DIR}/library.zip"

if [[ -f "${LIB_DIR}/RNS/vendor/umsgpack.py" || -f "${LIB_DIR}/RNS/vendor/umsgpack.pyc" ]]; then
    echo "RNS.vendor.umsgpack bundled under lib/RNS/vendor"
    exit 0
fi

if [[ -d "${LIB_DIR}/RNS/vendor" ]]; then
    hit="$(
        find "${LIB_DIR}/RNS/vendor" -maxdepth 1 -type f \
            \( -name 'umsgpack.py' -o -name 'umsgpack.pyc' -o -name 'umsgpack.*.pyc' \) \
            2>/dev/null | head -n 1 || true
    )"
    if [[ -n "${hit}" ]]; then
        echo "RNS.vendor.umsgpack bundled at ${hit}"
        exit 0
    fi
fi

if [[ -f "${LIBRARY_ZIP}" ]] && unzip -l "${LIBRARY_ZIP}" | grep -E -q 'RNS/vendor/umsgpack(\.py|\.pyc|/)?'; then
    echo "RNS.vendor.umsgpack found in lib/library.zip"
    exit 0
fi

echo "RNS.vendor.umsgpack missing from cx_Freeze output under ${BUILD_EXE}" >&2
echo "  Add RNS.vendor / RNS.vendor.umsgpack to cx_setup.py packages/includes." >&2
exit 1
