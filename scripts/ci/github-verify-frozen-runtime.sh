#!/usr/bin/env bash
# Run import probes inside the cx_Freeze binary (aiohttp/email/LXST natives).
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

EXE=""
for name in ReticulumMeshChatX ReticulumMeshChatX.exe; do
    if [[ -x "${BUILD_EXE}/${name}" ]] || [[ -f "${BUILD_EXE}/${name}" ]]; then
        EXE="${BUILD_EXE}/${name}"
        break
    fi
done

if [[ -z "${EXE}" ]]; then
    echo "frozen runtime verify: backend executable not found under ${BUILD_EXE}" >&2
    exit 1
fi

if [[ ! -d "${BUILD_EXE}/lib/email" ]]; then
    echo "frozen runtime verify: lib/email missing (stdlib email must not live only in library.zip)" >&2
    exit 1
fi

if [[ ! -f "${BUILD_EXE}/lib/email/header.py" ]]; then
    shopt -s nullglob
    headers=("${BUILD_EXE}/lib/email/header"*.pyc)
    shopt -u nullglob
    if [[ ${#headers[@]} -eq 0 ]]; then
        echo "frozen runtime verify: email.header module missing under lib/email" >&2
        exit 1
    fi
fi

"${EXE}" --meshchatx-run-module meshchatx.src.backend.frozen_freeze_probe
echo "frozen runtime verify: OK (${EXE})"
