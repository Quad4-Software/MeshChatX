#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENDOR_DIR="${1:-${ROOT_DIR}/android/vendor}"
JNI_LIBS_DIR="${2:-${ROOT_DIR}/android/app/src/main/jniLibs}"
ABI_LIST="${3:-arm64-v8a,x86_64,armeabi-v7a}"

abi_to_tag() {
    case "$1" in
        arm64-v8a) echo "arm64_v8a" ;;
        x86_64) echo "x86_64" ;;
        armeabi-v7a) echo "armeabi_v7a" ;;
        *) echo "Unsupported ABI: $1" >&2; exit 1 ;;
    esac
}

if [[ ! -d "${VENDOR_DIR}" ]]; then
    echo "Missing vendor directory: ${VENDOR_DIR}" >&2
    exit 1
fi

for abi in ${ABI_LIST//,/ }; do
    tag="$(abi_to_tag "${abi}")"
    lib_wheel="$(ls "${VENDOR_DIR}"/chaquopy_libcodec2-*-android_*_"${tag}".whl 2>/dev/null | tail -n 1 || true)"
    if [[ -z "${lib_wheel}" ]]; then
        echo "No chaquopy_libcodec2 wheel for ${abi} under ${VENDOR_DIR}" >&2
        exit 1
    fi
    dest_dir="${JNI_LIBS_DIR}/${abi}"
    mkdir -p "${dest_dir}"
    unzip -p "${lib_wheel}" chaquopy/lib/libcodec2.so > "${dest_dir}/libcodec2.so"
    echo "Synced ${dest_dir}/libcodec2.so from $(basename "${lib_wheel}")"
done
