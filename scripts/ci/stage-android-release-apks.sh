#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
# Copy signed Android APKs into DEST, renaming
# ReticulumMeshChatX-vVERSION-android-universal-signed.apk
# to ReticulumMeshChatX-vVERSION-android-universal.apk for GitHub release assets.
set -euo pipefail

SRC="${1:-android/app/build/outputs/apk/release}"
DEST="${2:-android-apks-for-draft}"

if [[ ! -d "${SRC}" ]]; then
    echo "Source directory missing: ${SRC}" >&2
    exit 1
fi

mkdir -p "${DEST}"

shopt -s nullglob
signed=("${SRC}"/*-signed.apk)
shopt -u nullglob

if [[ ${#signed[@]} -eq 0 ]]; then
    echo "Expected *-signed.apk under ${SRC} (dev and master draft releases use the same release-signed APK)." >&2
    exit 1
fi

copied=0
for src in "${signed[@]}"; do
    base="$(basename "${src}")"
    dest_name="${base%-signed.apk}.apk"
    if [[ "${dest_name}" == "${base}" ]]; then
        echo "Could not strip -signed suffix from ${base}" >&2
        exit 1
    fi
    if [[ ! "${dest_name}" =~ ^ReticulumMeshChatX-v.+-android-(universal|arm64-v8a|armeabi-v7a|x86_64)\.apk$ ]]; then
        echo "Release APK name ${dest_name} does not match ReticulumMeshChatX-v*-android-universal.apk" >&2
        exit 1
    fi
    cp -v "${src}" "${DEST}/${dest_name}"
    copied=$((copied + 1))
done

echo "Staged ${copied} Android release APK(s) under ${DEST}"
