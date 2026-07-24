#!/usr/bin/env bash
# Verify cx_Freeze bundles Landlock / AppContainer / Seccomp sandbox modules.
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
REQUIRED=(
    "meshchatx/src/backend/landlock_sandbox.py"
    "meshchatx/src/backend/appcontainer_sandbox.py"
    "meshchatx/src/backend/appcontainer_launcher.py"
    "meshchatx/src/backend/seccomp_sandbox.py"
)

missing=0
for rel in "${REQUIRED[@]}"; do
    if [[ -f "${LIB_DIR}/${rel}" ]]; then
        echo "found ${rel}"
        continue
    fi
    LIBRARY_ZIP="${LIB_DIR}/library.zip"
    if [[ -f "${LIBRARY_ZIP}" ]] && unzip -l "${LIBRARY_ZIP}" | grep -Fq "${rel}"; then
        echo "found ${rel} in library.zip"
        continue
    fi
    echo "missing sandbox module: ${rel}" >&2
    missing=1
done

if [[ "${missing}" -ne 0 ]]; then
    exit 1
fi

echo "FS sandbox modules present under ${BUILD_EXE}"
