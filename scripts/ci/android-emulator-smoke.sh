#!/usr/bin/env bash
# Install a MeshChatX APK on a running emulator/device, launch MainActivity,
# and fail if the Chaquopy backend does not become healthy.
#
# Expects: adb on PATH, one device/emulator online, APK path as $1 or MESHCHATX_APK.
set -euo pipefail

PACKAGE="${MESHCHATX_ANDROID_PACKAGE:-com.meshchatx}"
ACTIVITY="${MESHCHATX_ANDROID_ACTIVITY:-com.meshchatx/.MainActivity}"
STATUS_PATH="${MESHCHATX_SMOKE_STATUS_PATH:-/api/v1/status}"
TIMEOUT_SEC="${MESHCHATX_SMOKE_TIMEOUT_SEC:-180}"
LOGCAT_TAG_FILTER="${MESHCHATX_SMOKE_LOGCAT_FILTER:-Python|meshchat|MeshChat|chaquo|AndroidRuntime}"

APK="${1:-${MESHCHATX_APK:-}}"
if [[ -z "${APK}" ]]; then
    echo "usage: $0 <path-to.apk>" >&2
    exit 2
fi
if [[ ! -f "${APK}" ]]; then
    echo "APK not found: ${APK}" >&2
    exit 2
fi

if ! command -v adb >/dev/null 2>&1; then
    echo "adb not found on PATH" >&2
    exit 2
fi

adb wait-for-device
deadline=$((SECONDS + 120))
until adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx '1'; do
    if (( SECONDS >= deadline )); then
        echo "emulator did not finish booting within 120s" >&2
        exit 1
    fi
    sleep 2
done

echo "Installing ${APK}"
adb install -r -t --no-incremental "${APK}"

echo "Clearing logcat and launching ${ACTIVITY}"
adb logcat -c || true
adb shell am force-stop "${PACKAGE}" || true
adb shell am start -W -n "${ACTIVITY}"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/meshchatx-android-smoke.XXXXXX")"
trap 'rm -rf "${workdir}"' EXIT
logcat_file="${workdir}/logcat.txt"
adb logcat -v time >"${logcat_file}" &
logcat_pid=$!
cleanup_logcat() {
    kill "${logcat_pid}" >/dev/null 2>&1 || true
    wait "${logcat_pid}" >/dev/null 2>&1 || true
}
trap 'cleanup_logcat; rm -rf "${workdir}"' EXIT

fail_with_logs() {
    local reason="$1"
    echo "::error::Android emulator smoke failed: ${reason}"
    echo "---- logcat (filtered) ----"
    grep -E "${LOGCAT_TAG_FILTER}|PyException|SystemExit|ModuleNotFoundError|StorageLock|backend failed|Error starting MeshChatX" \
        "${logcat_file}" | tail -n 200 || true
    echo "---- logcat (tail) ----"
    tail -n 120 "${logcat_file}" || true
    exit 1
}

probe_status_ok() {
    # Probe from inside the emulator (server binds 127.0.0.1 on-device).
    # Prefer toybox wget (API 30+ images); fall back to python if present.
    local body=""
    if adb shell "command -v wget >/dev/null 2>&1" >/dev/null 2>&1; then
        body="$(adb shell "wget -qO- --no-check-certificate https://127.0.0.1:8000${STATUS_PATH}" 2>/dev/null | tr -d '\r' || true)"
        if [[ -z "${body}" ]]; then
            body="$(adb shell "wget -qO- http://127.0.0.1:8000${STATUS_PATH}" 2>/dev/null | tr -d '\r' || true)"
        fi
    elif adb shell "command -v curl >/dev/null 2>&1" >/dev/null 2>&1; then
        body="$(adb shell "curl -ksS --max-time 3 https://127.0.0.1:8000${STATUS_PATH}" 2>/dev/null | tr -d '\r' || true)"
        if [[ -z "${body}" ]]; then
            body="$(adb shell "curl -fsS --max-time 3 http://127.0.0.1:8000${STATUS_PATH}" 2>/dev/null | tr -d '\r' || true)"
        fi
    else
        # Escape path for embedding in a double-quoted adb shell command.
        local py_path
        py_path="$(printf '%s' "${STATUS_PATH}" | sed 's/\\/\\\\/g; s/"/\\"/g')"
        body="$(
            adb shell "python3 -c \"
import ssl, urllib.request
ctx = ssl._create_unverified_context()
urls = (
    ('https://127.0.0.1:8000${py_path}', ctx),
    ('http://127.0.0.1:8000${py_path}', None),
)
for url, context in urls:
    try:
        kwargs = {'timeout': 3}
        if context is not None:
            kwargs['context'] = context
        print(urllib.request.urlopen(url, **kwargs).read().decode())
        break
    except Exception:
        pass
\"" 2>/dev/null | tr -d '\r' || true
        )"
    fi
    printf '%s' "${body}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'
}

echo "Waiting up to ${TIMEOUT_SEC}s for backend health (${STATUS_PATH})"
deadline=$((SECONDS + TIMEOUT_SEC))
healthy=0
while (( SECONDS < deadline )); do
    if grep -Eiq 'PyException|ModuleNotFoundError: No module named|SystemExit: 1|MeshChatX backend failed|Error starting MeshChatX server' \
        "${logcat_file}"; then
        fail_with_logs "fatal backend error seen in logcat"
    fi

    if probe_status_ok; then
        healthy=1
        break
    fi

    sleep 3
done

if [[ "${healthy}" -ne 1 ]]; then
    fail_with_logs "backend /api/v1/status did not become ok within ${TIMEOUT_SEC}s"
fi

echo "Android emulator smoke OK: ${STATUS_PATH} returned status=ok"
grep -E "${LOGCAT_TAG_FILTER}" "${logcat_file}" | tail -n 40 || true
