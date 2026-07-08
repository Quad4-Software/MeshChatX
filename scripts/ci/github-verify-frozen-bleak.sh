#!/usr/bin/env bash
# Verify cx_Freeze bundled bleak for desktop RNode BLE support.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_EXE="${1:-${ROOT}/build/exe}"

if [[ ! -d "${BUILD_EXE}" ]]; then
    echo "cx_Freeze output not found at ${BUILD_EXE}" >&2
    exit 1
fi

LIB_DIR="${BUILD_EXE}/lib"
if [[ -d "${LIB_DIR}/bleak" ]]; then
    echo "bleak bundled at lib/bleak"
    exit 0
fi

LIBRARY_ZIP="${LIB_DIR}/library.zip"
if [[ -f "${LIBRARY_ZIP}" ]] && unzip -l "${LIBRARY_ZIP}" | grep -q bleak; then
    echo "bleak found in lib/library.zip"
    exit 0
fi

echo "bleak missing from cx_Freeze output under ${BUILD_EXE}" >&2
exit 1
