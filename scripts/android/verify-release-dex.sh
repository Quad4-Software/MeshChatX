#!/usr/bin/env bash
# Fail the release build when R8 stripped classes that Python loads
# reflectively via jclass(). These have no Java call sites so ProGuard
# cannot see them; a missing keep rule produces an APK that installs
# but silently disables LocalLink (WiFi Aware/Direct, hotspot, NFC).
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <release-apk> [apk...]" >&2
    exit 2
fi

REQUIRED_CLASSES=(
    "org/meshchatx/locallink/LocalLink"
    "org/meshchatx/locallink/PythonLocalLink"
    "org/meshchatx/locallink/AwareSession"
    "org/meshchatx/locallink/PythonAware"
    "org/meshchatx/locallink/NfcShare"
    "org/meshchatx/locallink/PythonNfc"
    "org/meshchatx/locallink/NfcShareService"
)

status=0
for apk in "$@"; do
    if [ ! -f "$apk" ]; then
        echo "verify-release-dex: missing apk: $apk" >&2
        status=1
        continue
    fi
    workdir="$(mktemp -d)"
    if ! unzip -o -q "$apk" 'classes*.dex' -d "$workdir"; then
        echo "verify-release-dex: no dex files in $apk" >&2
        rm -rf "$workdir"
        status=1
        continue
    fi
    for cls in "${REQUIRED_CLASSES[@]}"; do
        if ! grep -l -F "L${cls};" "$workdir"/classes*.dex >/dev/null 2>&1; then
            echo "verify-release-dex: $apk missing $cls (R8 stripped? check proguard-rules.pro)" >&2
            status=1
        fi
    done
    rm -rf "$workdir"
done

if [ "$status" -eq 0 ]; then
    echo "verify-release-dex: all reflection-loaded classes present"
fi
exit "$status"
