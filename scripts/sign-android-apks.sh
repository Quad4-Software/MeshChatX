#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Sign Android release APKs (and optionally add SourceStamp).

Required env vars:
  SIGNING_KEYSTORE_PATH     Path to signing keystore (.jks/.keystore)
  SIGNING_KEY_ALIAS         Alias of signing key
  SIGNING_KEYSTORE_PASSWORD Keystore password
  SIGNING_KEY_PASSWORD      Key password (defaults to SIGNING_KEYSTORE_PASSWORD)

Optional env vars:
  ANDROID_HOME              Android SDK root (or ANDROID_SDK_ROOT)
  APK_GLOB                  Glob for unsigned APKs
                            (default: android/app/build/outputs/apk/release/*-unsigned.apk)
  ENABLE_SOURCESTAMP        true/false (default: false)
  SOURCESTAMP_KEYSTORE_PATH Path to SourceStamp keystore
  SOURCESTAMP_KEY_ALIAS     Alias in SourceStamp keystore
  SOURCESTAMP_KEYSTORE_PASSWORD SourceStamp keystore password
  SOURCESTAMP_KEY_PASSWORD  SourceStamp key password

Output:
  Creates sibling files for each unsigned APK:
    *-aligned.apk
    *-signed.apk

Examples:
  SIGNING_KEYSTORE_PATH=android/keystore/meshchatx-release.jks \
  SIGNING_KEY_ALIAS=meshchatx-release \
  SIGNING_KEYSTORE_PASSWORD='...' \
  SIGNING_KEY_PASSWORD='...' \
  bash scripts/sign-android-apks.sh

  SIGNING_KEYSTORE_PATH=android/keystore/meshchatx-release.jks \
  SIGNING_KEY_ALIAS=meshchatx-release \
  SIGNING_KEYSTORE_PASSWORD='...' \
  SIGNING_KEY_PASSWORD='...' \
  ENABLE_SOURCESTAMP=true \
  SOURCESTAMP_KEYSTORE_PATH=android/keystore/meshchatx-stamp.jks \
  SOURCESTAMP_KEY_ALIAS=meshchatx-stamp \
  SOURCESTAMP_KEYSTORE_PASSWORD='...' \
  SOURCESTAMP_KEY_PASSWORD='...' \
  bash scripts/sign-android-apks.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

require_env() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        echo "Missing required env var: ${name}" >&2
        exit 1
    fi
}

require_env SIGNING_KEYSTORE_PATH
require_env SIGNING_KEY_ALIAS
require_env SIGNING_KEYSTORE_PASSWORD
SIGNING_KEY_PASSWORD="${SIGNING_KEY_PASSWORD:-${SIGNING_KEYSTORE_PASSWORD}}"

ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "${ANDROID_HOME}" ]]; then
    echo "Set ANDROID_HOME (or ANDROID_SDK_ROOT) to your Android SDK path." >&2
    exit 1
fi

BT_DIR="$(ls -d "${ANDROID_HOME}"/build-tools/* 2>/dev/null | sort -V | tail -n 1)"
if [[ -z "${BT_DIR}" ]]; then
    echo "No Android build-tools found under ${ANDROID_HOME}/build-tools." >&2
    exit 1
fi
if [[ ! -x "${BT_DIR}/zipalign" || ! -x "${BT_DIR}/apksigner" ]]; then
    echo "Missing zipalign/apksigner in ${BT_DIR}. Install build-tools via sdkmanager." >&2
    exit 1
fi

APK_GLOB="${APK_GLOB:-android/app/build/outputs/apk/release/*-unsigned.apk}"
shopt -s nullglob
APKS=( ${APK_GLOB} )
shopt -u nullglob
if [[ ${#APKS[@]} -eq 0 ]]; then
    echo "No unsigned APKs matched: ${APK_GLOB}" >&2
    exit 1
fi

ENABLE_SOURCESTAMP="${ENABLE_SOURCESTAMP:-false}"
if [[ "${ENABLE_SOURCESTAMP}" == "true" ]]; then
    require_env SOURCESTAMP_KEYSTORE_PATH
    require_env SOURCESTAMP_KEY_ALIAS
    require_env SOURCESTAMP_KEYSTORE_PASSWORD
    SOURCESTAMP_KEY_PASSWORD="${SOURCESTAMP_KEY_PASSWORD:-${SOURCESTAMP_KEYSTORE_PASSWORD}}"
fi

for apk in "${APKS[@]}"; do
    base="${apk%-unsigned.apk}"
    aligned="${base}-aligned.apk"
    signed="${base}-signed.apk"

    echo "Aligning ${apk}"
    "${BT_DIR}/zipalign" -p -f 4 "${apk}" "${aligned}"

    sign_args=(
        sign
        --ks "${SIGNING_KEYSTORE_PATH}"
        --ks-key-alias "${SIGNING_KEY_ALIAS}"
        --ks-pass "pass:${SIGNING_KEYSTORE_PASSWORD}"
        --key-pass "pass:${SIGNING_KEY_PASSWORD}"
        --out "${signed}"
    )

    if [[ "${ENABLE_SOURCESTAMP}" == "true" ]]; then
        sign_args+=(
            --stamp-signer
            --stamp-ks "${SOURCESTAMP_KEYSTORE_PATH}"
            --stamp-key-alias "${SOURCESTAMP_KEY_ALIAS}"
            --stamp-ks-pass "pass:${SOURCESTAMP_KEYSTORE_PASSWORD}"
            --stamp-key-pass "pass:${SOURCESTAMP_KEY_PASSWORD}"
        )
    fi

    echo "Signing ${aligned}"
    "${BT_DIR}/apksigner" "${sign_args[@]}" "${aligned}"

    echo "Verifying ${signed}"
    "${BT_DIR}/apksigner" verify --verbose --print-certs "${signed}"
done

echo "Done."
