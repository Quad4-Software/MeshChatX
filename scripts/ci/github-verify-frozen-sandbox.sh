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
LIBRARY_ZIP="${LIB_DIR}/library.zip"
REQUIRED_STEMS=(
    "landlock_sandbox"
    "appcontainer_sandbox"
    "appcontainer_launcher"
    "seccomp_sandbox"
)

module_present() {
    local stem="$1"
    local hit

    hit="$(
        find "${LIB_DIR}" -type f \
            \( -name "${stem}.py" -o -name "${stem}.pyc" -o -name "${stem}.*.pyc" \) \
            2>/dev/null | head -n 1 || true
    )"
    if [[ -n "${hit}" ]]; then
        echo "found ${hit#"${LIB_DIR}"/}"
        return 0
    fi

    if [[ -f "${LIBRARY_ZIP}" ]]; then
        if unzip -l "${LIBRARY_ZIP}" | grep -Eiq "${stem}\\.(py|pyc)([^[:alnum:_].]|$)"; then
            echo "found ${stem} in library.zip"
            return 0
        fi
    fi

    return 1
}

missing=0
for stem in "${REQUIRED_STEMS[@]}"; do
    if module_present "${stem}"; then
        continue
    fi
    echo "missing sandbox module: ${stem}" >&2
    missing=1
done

if [[ "${missing}" -ne 0 ]]; then
    exit 1
fi

echo "FS sandbox modules present under ${BUILD_EXE}"
