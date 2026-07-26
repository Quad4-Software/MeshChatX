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
DEVICE_HTTP_PORT="${MESHCHATX_SMOKE_DEVICE_PORT:-8000}"
FORWARD_LOCAL_PORT="${MESHCHATX_SMOKE_FORWARD_PORT:-18080}"
PROBE_CURL_MAX_TIME="${MESHCHATX_SMOKE_PROBE_MAX_TIME:-5}"
last_probe_body=""

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

teardown_adb_forward() {
    adb forward --remove "tcp:${FORWARD_LOCAL_PORT}" >/dev/null 2>&1 || true
}

setup_adb_forward() {
    teardown_adb_forward
    adb forward "tcp:${FORWARD_LOCAL_PORT}" "tcp:${DEVICE_HTTP_PORT}"
}

trap 'teardown_adb_forward; cleanup_logcat; rm -rf "${workdir}"' EXIT

fail_with_logs() {
    local reason="$1"
    echo "::error::Android emulator smoke failed: ${reason}"
    if [[ -n "${last_probe_body}" ]]; then
        echo "---- last /api/v1/status probe body ----"
        printf '%s\n' "${last_probe_body}"
    fi
    echo "---- logcat (filtered) ----"
    grep -E "${LOGCAT_TAG_FILTER}|PyException|SystemExit|ModuleNotFoundError|StorageLock|backend failed|Error starting MeshChatX" \
        "${logcat_file}" | tail -n 200 || true
    echo "---- logcat (tail) ----"
    tail -n 120 "${logcat_file}" || true
    exit 1
}

status_body_is_healthy() {
    local body="$1"
    if [[ -z "${body}" ]]; then
        return 1
    fi
    if printf '%s' "${body}" | grep -qE '"status"[[:space:]]*:[[:space:]]*"failed"'; then
        return 1
    fi
    # ok: network ready. starting: HTTP up while RNS finishes (normal on Android boot).
    printf '%s' "${body}" | grep -qE '"status"[[:space:]]*:[[:space:]]*"(ok|starting)"'
}

probe_status_via_host_forward() {
    local body=""
    if ! command -v curl >/dev/null 2>&1; then
        return 1
    fi
    body="$(
        curl -ksS --max-time "${PROBE_CURL_MAX_TIME}" \
            "https://127.0.0.1:${FORWARD_LOCAL_PORT}${STATUS_PATH}" 2>/dev/null || true
    )"
    if [[ -z "${body}" ]]; then
        body="$(
            curl -fsS --max-time "${PROBE_CURL_MAX_TIME}" \
                "http://127.0.0.1:${FORWARD_LOCAL_PORT}${STATUS_PATH}" 2>/dev/null || true
        )"
    fi
    if [[ -z "${body}" ]]; then
        return 1
    fi
    last_probe_body="${body}"
    status_body_is_healthy "${body}"
}

probe_status_via_device_shell() {
    # Fallback when host curl or adb forward is unavailable.
    local body=""
    local device_base="127.0.0.1:${DEVICE_HTTP_PORT}"
    if adb shell "command -v curl >/dev/null 2>&1" >/dev/null 2>&1; then
        body="$(
            adb shell "curl -ksS --max-time ${PROBE_CURL_MAX_TIME} https://${device_base}${STATUS_PATH}" \
                2>/dev/null | tr -d '\r' || true
        )"
        if [[ -z "${body}" ]]; then
            body="$(
                adb shell "curl -fsS --max-time ${PROBE_CURL_MAX_TIME} http://${device_base}${STATUS_PATH}" \
                    2>/dev/null | tr -d '\r' || true
            )"
        fi
    elif adb shell "command -v wget >/dev/null 2>&1" >/dev/null 2>&1; then
        body="$(
            adb shell "wget -qO- -T ${PROBE_CURL_MAX_TIME} --no-check-certificate https://${device_base}${STATUS_PATH}" \
                2>/dev/null | tr -d '\r' || true
        )"
        if [[ -z "${body}" ]]; then
            body="$(
                adb shell "wget -qO- -T ${PROBE_CURL_MAX_TIME} http://${device_base}${STATUS_PATH}" \
                    2>/dev/null | tr -d '\r' || true
            )"
        fi
    else
        local py_path
        py_path="$(printf '%s' "${STATUS_PATH}" | sed 's/\\/\\\\/g; s/"/\\"/g')"
        body="$(
            adb shell "python3 -c \"
import ssl, urllib.request
ctx = ssl._create_unverified_context()
urls = (
    ('https://${device_base}${py_path}', ctx),
    ('http://${device_base}${py_path}', None),
)
for url, context in urls:
    try:
        kwargs = {'timeout': ${PROBE_CURL_MAX_TIME}}
        if context is not None:
            kwargs['context'] = context
        print(urllib.request.urlopen(url, **kwargs).read().decode())
        break
    except Exception:
        pass
\"" 2>/dev/null | tr -d '\r' || true
        )"
    fi
    if [[ -z "${body}" ]]; then
        return 1
    fi
    last_probe_body="${body}"
    status_body_is_healthy "${body}"
}

probe_status_ok() {
    if probe_status_via_host_forward; then
        return 0
    fi
    probe_status_via_device_shell
}

setup_adb_forward

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
    fail_with_logs "backend ${STATUS_PATH} did not return ok or starting within ${TIMEOUT_SEC}s"
fi

echo "Android emulator smoke OK: ${STATUS_PATH} -> ${last_probe_body}"
grep -E "${LOGCAT_TAG_FILTER}" "${logcat_file}" | tail -n 40 || true
