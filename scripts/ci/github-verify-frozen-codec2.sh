#!/usr/bin/env bash
# Fail if frozen pycodec2 cannot resolve libcodec2.
#
# Usage:
#   github-verify-frozen-codec2.sh [build/exe]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_EXE="${1:-${ROOT}/build/exe}"

if [[ ! -d "${BUILD_EXE}" ]]; then
    echo "frozen codec2 verify: cx_Freeze output not found at ${BUILD_EXE}" >&2
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

PKG="${BUILD_EXE}/lib/pycodec2"
if [[ ! -d "${PKG}" ]]; then
    echo "frozen codec2 verify: missing ${PKG}" >&2
    exit 1
fi

shopt -s nullglob
exts=("${PKG}"/pycodec2*.so "${PKG}"/pycodec2*.pyd "${PKG}"/pycodec2*.dylib)
shopt -u nullglob
if [[ ${#exts[@]} -eq 0 ]]; then
    echo "frozen codec2 verify: no pycodec2 extension under ${PKG}" >&2
    exit 1
fi
EXT="${exts[0]}"

shopt -s nullglob
candidates=(
    "${PKG}"/libcodec2.dylib
    "${PKG}"/libcodec2.so
    "${PKG}"/libcodec2.dll
    "${PKG}"/.dylibs/libcodec2*.dylib
    "${BUILD_EXE}/lib"/libcodec2*.dylib
    "${BUILD_EXE}/lib"/libcodec2.so*
    "${BUILD_EXE}/lib"/libcodec2.dll
)
shopt -u nullglob

libs=()
for _lib in "${candidates[@]}"; do
    if [[ -f "${_lib}" ]]; then
        libs+=("${_lib}")
    fi
done

if [[ "$(uname -s)" == "Darwin" && ${#libs[@]} -eq 0 ]]; then
    echo "frozen codec2 verify: libcodec2 missing next to ${EXT}" >&2
    echo "  expected lib/pycodec2/libcodec2.dylib or lib/libcodec2*.dylib" >&2
    exit 1
fi

resolve_dep() {
    local dep="$1"
    local so_dir
    so_dir="$(cd "$(dirname "${EXT}")" && pwd)"
    case "${dep}" in
    @executable_path/*)
        printf '%s\n' "${BUILD_EXE}/${dep#@executable_path/}"
        ;;
    @loader_path/*)
        printf '%s\n' "${so_dir}/${dep#@loader_path/}"
        ;;
    @rpath/*)
        printf '%s\n' "${BUILD_EXE}/lib/${dep#@rpath/}"
        ;;
    /*)
        printf '%s\n' "${dep}"
        ;;
    *)
        printf '%s\n' "${so_dir}/${dep}"
        ;;
    esac
}

if [[ "$(uname -s)" == "Darwin" ]] && command -v otool >/dev/null 2>&1; then
    while IFS= read -r dep; do
        [[ -n "${dep}" ]] || continue
        case "${dep}" in
        /opt/homebrew/* | /usr/local/* | /opt/local/*)
            echo "frozen codec2 verify: ${EXT} still links absolute ${dep}" >&2
            echo "  rewrite to @loader_path/libcodec2.dylib before shipping" >&2
            exit 1
            ;;
        esac
        resolved="$(resolve_dep "${dep}")"
        if [[ ! -f "${resolved}" ]]; then
            echo "frozen codec2 verify: ${EXT} needs ${dep}" >&2
            echo "  resolved missing path: ${resolved}" >&2
            exit 1
        fi
    done < <(otool -L "${EXT}" | awk '/libcodec2/{print $1}')
fi

if [[ ${#libs[@]} -gt 0 ]]; then
    echo "frozen codec2 verify: OK (${EXT} + ${libs[0]})"
else
    echo "frozen codec2 verify: OK (${EXT}, libcodec2 not bundled)"
fi
