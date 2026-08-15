#!/usr/bin/env bash
# Run import probes inside the cx_Freeze binary (aiohttp/email/LXST natives).
# On Apple Silicon, darwin-x64 trees must be exec'd with arch -x86_64. A
# universal2 freeze stub otherwise starts as arm64 and dlopen fails on
# x86_64 zlib.cpython-*-darwin.so.
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

if [[ ! -x "${EXE}" ]]; then
    chmod +x "${EXE}"
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

run_prefix=()
if [[ "$(uname -s)" == "Darwin" ]]; then
    host_arch="$(uname -m)"
    case "${host_arch}" in
    x86_64 | amd64) host_arch=x86_64 ;;
    arm64 | aarch64) host_arch=arm64 ;;
    esac
    want=""
    case "${BUILD_EXE}" in
    *darwin-x64*) want=x86_64 ;;
    *darwin-arm64*) want=arm64 ;;
    esac
    exe_archs=""
    if command -v lipo >/dev/null 2>&1; then
        exe_archs="$(lipo -archs "${EXE}" 2>/dev/null || true)"
    fi
    if [[ -z "${want}" && -n "${exe_archs}" ]]; then
        want="$(awk '{print $1}' <<<"${exe_archs}")"
    fi
    if [[ -n "${want}" && -n "${exe_archs}" ]] && ! grep -qw "${want}" <<<"${exe_archs}"; then
        echo "frozen runtime verify: ${EXE} archs=${exe_archs} cannot run as ${want}" >&2
        echo "  darwin-x64 must ship an x86_64 (or universal) ReticulumMeshChatX stub." >&2
        echo "  thin-backend-mach-o.sh must lipo-thin that executable, not only .so/.dylib." >&2
        exit 1
    fi
    if [[ -n "${want}" && "${want}" != "${host_arch}" ]]; then
        if ! command -v arch >/dev/null 2>&1; then
            echo "frozen runtime verify: need arch -${want} to run ${EXE} on ${host_arch}" >&2
            exit 1
        fi
        if ! arch "-${want}" /usr/bin/true >/dev/null 2>&1; then
            echo "frozen runtime verify: arch -${want} failed on host ${host_arch}" >&2
            echo "  Install Rosetta 2 to probe the darwin-x64 freeze tree on Apple Silicon." >&2
            exit 1
        fi
        run_prefix=(arch "-${want}")
        echo "frozen runtime verify: using arch -${want} (host ${host_arch})"
    fi
fi

if [[ ${#run_prefix[@]} -gt 0 ]]; then
    "${run_prefix[@]}" "${EXE}" --meshchatx-run-module meshchatx.src.backend.frozen_freeze_probe
else
    "${EXE}" --meshchatx-run-module meshchatx.src.backend.frozen_freeze_probe
fi
echo "frozen runtime verify: OK (${EXE})"
