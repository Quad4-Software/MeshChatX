#!/usr/bin/env bash
# Smoke-test a MeshChatX AppImage against its bundled stub backend.
#
# Usage:
#   scripts/ci/test-appimage.sh <path-to.AppImage>
#
# Requires a display. On headless CI use xvfb-run:
#   xvfb-run -a scripts/ci/test-appimage.sh /path/to/App.AppImage
#
# The AppImage must have been built with a stub backend baked in
# (BACKEND_DIR pointing at the compiled scripts/appimage-stub-backend.go
# binary). For a production AppImage carrying the real backend this test
# still works: the real backend answers /api/v1/status but nothing POSTs
# to /result, so the bridge check will fail — use a stub build for CI.
set -uo pipefail

AI="$(readlink -f "${1:-}")"
if [[ -z "$AI" || ! -f "$AI" ]]; then
  echo "usage: $0 <path-to.AppImage>" >&2
  exit 2
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "FAIL: no DISPLAY/WAYLAND_DISPLAY — run under xvfb-run for headless CI" >&2
  exit 2
fi

# Heavy scratch stays out of /tmp (small shared tmpfs on dev hosts).
WORK="${APPIMAGE_TEST_WORKDIR:-$(dirname "$AI")/appimage-test-work/$$}"
mkdir -p "$WORK"
RESULTS="$WORK/results.jsonl"
LOG="$WORK/app.log"
UNIQUE="com.meshchatx.appimage-test-p$$"
STORAGE="$WORK/storage"
RNS_DIR="$WORK/rns"
mkdir -p "$STORAGE" "$RNS_DIR"

PASS=0
FAIL=0
ok()   { PASS=$((PASS+1)); echo "PASS: $*"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL: $*"; }

kill_owned() {
  # Kill only processes belonging to OUR AppImage runs. WebKit helpers are
  # matched via /proc/exe: theirs must live in an AppDir that also contains
  # our shell binary — this avoids killing foreign AppImages' helpers.
  local sig="$1" pid args hit exe root
  while read -r pid args; do
    [[ -z "$pid" ]] && continue
    hit=0
    case "$args" in
      *meshchatx-desktop*)
        case "$args" in
          /mnt/projects/meshchatx/desktop/bin/meshchatx-desktop*) continue ;;
        esac
        hit=1 ;;
      *reticulum-meshchatx/backend*) hit=1 ;;
      *"Test App.AppImage"*|*"$AI"*) hit=1 ;;
      *webkitgtk-6.0*|*xdg-dbus-proxy*)
        # helpers run with cwd=$APPDIR; verify via exe that the AppDir is ours
        # (contains our shell binary) — never kill foreign AppImages' helpers
        exe=$(readlink /proc/$pid/exe 2>/dev/null)
        root="${exe%%/usr/lib/webkitgtk-6.0/*}"
        if [[ "$root" != "$exe" && -x "$root/usr/bin/meshchatx-desktop" ]]; then hit=1; fi ;;
    esac
    if [[ $hit -eq 1 ]]; then
      if [[ -n "$sig" ]]; then kill "$sig" "$pid" 2>/dev/null; else kill "$pid" 2>/dev/null; fi
    fi
  done < <(ps -eo pid=,args=)
  true
}
kill_owned_tree() { kill_owned ""; sleep 2; kill_owned -9; }
trap 'kill_owned_tree; rm -rf "$WORK/squashfs-root"' EXIT

echo "=== AppImage smoke test: $AI"

# ---- 0. basic artifact checks ----------------------------------------------
if "$AI" --appimage-version >/dev/null 2>&1; then
  ok "--appimage-version works: $("$AI" --appimage-version 2>/dev/null | head -1)"
else
  bad "--appimage-version failed"
fi

# ---- 1. extract + ldd checks ------------------------------------------------
EXTRACT_DIR="$WORK/extract"
mkdir -p "$EXTRACT_DIR"
( cd "$EXTRACT_DIR" && "$AI" --appimage-extract >/dev/null 2>&1 )
ROOT="$EXTRACT_DIR/squashfs-root"
if [[ ! -d "$ROOT" ]]; then
  bad "--appimage-extract produced no squashfs-root"
  echo "== $PASS passed, $FAIL failed =="
  exit 1
fi
ok "--appimage-extract ok ($(du -sh "$ROOT" | cut -f1))"

SHELL_BIN="$(find "$ROOT/usr/bin" -maxdepth 1 -type f -executable | head -1)"
if [[ -z "$SHELL_BIN" ]]; then bad "no executable in usr/bin"; else ok "shell binary: $SHELL_BIN"; fi

# ldd every ELF under usr/bin + libwebkitgtk + WebKit helpers with AppRun env
LD_PATH="$ROOT/usr/lib:$ROOT/usr/lib/x86_64-linux-gnu"
missing=0
for f in "$SHELL_BIN" \
         "$ROOT"/usr/lib/libwebkitgtk-6.0.so* \
         "$ROOT"/usr/lib/webkitgtk-6.0/WebKitWebProcess \
         "$ROOT"/usr/lib/webkitgtk-6.0/WebKitNetworkProcess \
         "$ROOT"/usr/lib/webkitgtk-6.0/WebKitGPUProcess; do
  [[ -e "$f" ]] || continue
  out=$(LD_LIBRARY_PATH="$LD_PATH" ldd "$f" 2>&1 | grep "not found")
  if [[ -n "$out" ]]; then
    bad "ldd $f: $out"
    missing=1
  fi
done
[[ $missing -eq 0 ]] && ok "ldd: no missing libraries in shell/webkit binaries"

# desktop file validation
DESKTOP_FILE=$(find "$ROOT" -maxdepth 2 -name "*.desktop" | head -1)
if [[ -n "$DESKTOP_FILE" ]] && command -v desktop-file-validate >/dev/null; then
  if desktop-file-validate "$DESKTOP_FILE" >/dev/null 2>&1; then
    ok "desktop-file-validate: $(basename "$DESKTOP_FILE")"
  else
    bad "desktop-file-validate: $(desktop-file-validate "$DESKTOP_FILE" 2>&1 | head -3)"
  fi
fi
if [[ -n "$DESKTOP_FILE" ]] && grep -q "x-scheme-handler/lxmf" "$DESKTOP_FILE" \
   && grep -q "x-scheme-handler/rns" "$DESKTOP_FILE"; then
  ok "desktop file declares lxmf + rns scheme handlers"
else
  bad "desktop file missing lxmf/rns MimeType"
fi

# ---- helper: launch + wait for probe result ---------------------------------
launch_and_probe() {
  # $1 = label, $2 = env-prefix command string already set up by caller
  local label="$1"; shift
  : > "$RESULTS"
  rm -f "$LOG"
  echo "--- run: $label"
  # shellcheck disable=SC2086
  env DISPLAY="${DISPLAY:-:1.0}" \
      XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
      DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
      HOME="$HOME" PATH="$PATH" \
      STUB_RESULTS_FILE="$RESULTS" \
      MESHCHATX_UNIQUE_ID="$UNIQUE" \
      MESHCHATX_STORAGE_DIR="$STORAGE" \
      MESHCHATX_RNS_CONFIG_DIR="$RNS_DIR" \
      "$@" >"$LOG" 2>&1 &
  local pid=$!
  local waited=0
  while (( waited < 90 )); do
    if grep -q '"appVersion"' "$RESULTS" 2>/dev/null; then break; fi
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    # a dead child stays a zombie (kill -0 still succeeds) until wait
    [[ "$(ps -o stat= -p "$pid" 2>/dev/null | cut -c1)" == Z ]] && break
    sleep 2; waited=$((waited+2))
  done
  if grep -q '"appVersion"' "$RESULTS" 2>/dev/null; then
    local line
    line=$(grep '"appVersion"' "$RESULTS" | tail -1)
    if echo "$line" | grep -q '"hasDesktop":true' && echo "$line" | grep -q '"isSecureContext":true'; then
      ok "$label: probe result $line"
    else
      bad "$label: probe result missing flags: $line"
    fi
  else
    bad "$label: no /result within 90s (log tail: $(tail -3 "$LOG" | tr '\n' '|'))"
  fi
  # error scan
  if grep -qiE 'not found|Failed to load|error while loading|cannot open shared' "$LOG"; then
    bad "$label: error strings in log: $(grep -iE 'not found|Failed to load|error while loading|cannot open shared' "$LOG" | head -3 | tr '\n' '|')"
  else
    ok "$label: no missing-library/load errors in log"
  fi
  # helper processes spawned from OUR bundled path: exe must live under an
  # AppDir that also contains our shell binary (excludes foreign AppImages)
  local hp=0 p exe root
  for p in $(pgrep -f 'webkitgtk-6.0/WebKit' 2>/dev/null); do
    exe=$(readlink /proc/$p/exe 2>/dev/null)
    root="${exe%%/usr/lib/webkitgtk-6.0/*}"
    if [[ "$root" != "$exe" && -x "$root/usr/bin/meshchatx-desktop" ]]; then hp=1; break; fi
  done
  if [[ $hp -eq 1 ]]; then
    ok "$label: bundled WebKit helpers running"
  else
    bad "$label: no bundled WebKit helper processes found"
  fi
  kill_owned_tree
  wait "$pid" 2>/dev/null
  sleep 1
}

# ---- 2. path with spaces ------------------------------------------------------
SPACED="$WORK/dir with spaces"
mkdir -p "$SPACED"
cp "$AI" "$SPACED/Test App.AppImage"
chmod +x "$SPACED/Test App.AppImage"
launch_and_probe "spaces-path" "$SPACED/Test App.AppImage"

# ---- 3. nearly empty environment ---------------------------------------------
RESULTS2="$WORK/results-env-i.jsonl"
STUB_RESULTS_FILE="$RESULTS2" : > "$RESULTS2"
# custom launch for env -i (different results file)
: > "$RESULTS2"; rm -f "$LOG"
echo "--- run: env-i"
env -i HOME="$HOME" DISPLAY="${DISPLAY:-:1.0}" \
    XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
    PATH=/usr/local/bin:/usr/bin:/bin \
    STUB_RESULTS_FILE="$RESULTS2" MESHCHATX_UNIQUE_ID="$UNIQUE" \
    MESHCHATX_STORAGE_DIR="$STORAGE" MESHCHATX_RNS_CONFIG_DIR="$RNS_DIR" \
    "$AI" >"$LOG" 2>&1 &
PID_ENV=$!
w=0
while (( w < 90 )); do
  grep -q '"appVersion"' "$RESULTS2" 2>/dev/null && break
  kill -0 "$PID_ENV" 2>/dev/null || break
  [[ "$(ps -o stat= -p "$PID_ENV" 2>/dev/null | cut -c1)" == Z ]] && break
  sleep 2; w=$((w+2))
done
if grep -q '"appVersion"' "$RESULTS2" 2>/dev/null; then
  ok "env-i: probe result $(grep '"appVersion"' "$RESULTS2" | tail -1)"
else
  bad "env-i: no /result within 90s (log tail: $(tail -3 "$LOG" | tr '\n' '|'))"
fi
kill_owned_tree; wait "$PID_ENV" 2>/dev/null; sleep 1

# ---- 4. --appimage-extract-and-run -------------------------------------------
launch_and_probe "extract-and-run" "$AI" --appimage-extract-and-run

# ---- 5. single instance + protocol arg ---------------------------------------
RESULTS5="$WORK/results-si.jsonl"
STUB_RESULTS_FILE="$RESULTS5" : > "$RESULTS5"
: > "$RESULTS5"; rm -f "$LOG"
echo "--- run: single-instance primary"
env DISPLAY="${DISPLAY:-:1.0}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" HOME="$HOME" PATH="$PATH" \
    STUB_RESULTS_FILE="$RESULTS5" MESHCHATX_UNIQUE_ID="$UNIQUE" \
    MESHCHATX_STORAGE_DIR="$STORAGE" MESHCHATX_RNS_CONFIG_DIR="$RNS_DIR" \
    "$AI" >"$LOG" 2>&1 &
PID_MAIN=$!
w=0
while (( w < 90 )); do
  grep -q '"appVersion"' "$RESULTS5" 2>/dev/null && break
  kill -0 "$PID_MAIN" 2>/dev/null || break
  [[ "$(ps -o stat= -p "$PID_MAIN" 2>/dev/null | cut -c1)" == Z ]] && break
  sleep 2; w=$((w+2))
done
grep -q '"appVersion"' "$RESULTS5" 2>/dev/null \
  && ok "single-instance: primary probe ok" \
  || bad "single-instance: primary probe missing"

# second launch must exit quickly and hand off, and the running instance's
# page must receive the link (asserted via the stub's protocolLinks posts)
echo "--- run: second instance lxmf://abc"
SECONDS_START=$SECONDS
env DISPLAY="${DISPLAY:-:1.0}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" HOME="$HOME" PATH="$PATH" \
    STUB_RESULTS_FILE="$RESULTS5" MESHCHATX_UNIQUE_ID="$UNIQUE" \
    MESHCHATX_STORAGE_DIR="$STORAGE" MESHCHATX_RNS_CONFIG_DIR="$RNS_DIR" \
    "$AI" "lxmf://abc" >"$WORK/second.log" 2>&1
SECOND_RC=$?
ELAPSED=$((SECONDS - SECONDS_START))
if [[ $SECOND_RC -eq 0 && $ELAPSED -lt 30 ]]; then
  ok "second instance exited rc=$SECOND_RC in ${ELAPSED}s (handed off)"
else
  bad "second instance rc=$SECOND_RC elapsed=${ELAPSED}s"
fi
w=0
while (( w < 30 )); do
  grep -q '"protocolLinks".*lxmf://abc' "$RESULTS5" 2>/dev/null && break
  sleep 0.5; w=$((w+1))
done
if grep -q '"protocolLinks".*lxmf://abc' "$RESULTS5" 2>/dev/null; then
  ok "lxmf://abc delivered to page: $(grep 'protocolLinks' "$RESULTS5" | tail -1)"
else
  bad "lxmf://abc NOT delivered to page (results: $(tail -2 "$RESULTS5" | tr '\n' '|'))"
fi

# rns:// variant through the same second-instance path
echo "--- run: second instance rns://def456"
env DISPLAY="${DISPLAY:-:1.0}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" HOME="$HOME" PATH="$PATH" \
    STUB_RESULTS_FILE="$RESULTS5" MESHCHATX_UNIQUE_ID="$UNIQUE" \
    MESHCHATX_STORAGE_DIR="$STORAGE" MESHCHATX_RNS_CONFIG_DIR="$RNS_DIR" \
    "$AI" "rns://def456" >"$WORK/second-rns.log" 2>&1
RNS_RC=$?
w=0
while (( w < 30 )); do
  grep -q '"protocolLinks".*rns://def456' "$RESULTS5" 2>/dev/null && break
  sleep 0.5; w=$((w+1))
done
if [[ $RNS_RC -eq 0 ]] && grep -q '"protocolLinks".*rns://def456' "$RESULTS5" 2>/dev/null; then
  ok "rns://def456 delivered to page: $(grep 'protocolLinks' "$RESULTS5" | tail -1)"
else
  bad "rns://def456 NOT delivered (rc=$RNS_RC; results: $(tail -2 "$RESULTS5" | tr '\n' '|'))"
fi
kill_owned_tree; wait "$PID_MAIN" 2>/dev/null; sleep 1

# ---- 6. cold start with a link arg -------------------------------------------
RESULTS6="$WORK/results-cold.jsonl"
: > "$RESULTS6"; rm -f "$LOG"
echo "--- run: cold start lxmf://cold123"
env DISPLAY="${DISPLAY:-:1.0}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" HOME="$HOME" PATH="$PATH" \
    STUB_RESULTS_FILE="$RESULTS6" MESHCHATX_UNIQUE_ID="$UNIQUE" \
    MESHCHATX_STORAGE_DIR="$STORAGE" MESHCHATX_RNS_CONFIG_DIR="$RNS_DIR" \
    "$AI" "lxmf://cold123" >"$LOG" 2>&1 &
PID_COLD=$!
w=0
while (( w < 90 )); do
  grep -q '"appVersion"' "$RESULTS6" 2>/dev/null && break
  kill -0 "$PID_COLD" 2>/dev/null || break
  [[ "$(ps -o stat= -p "$PID_COLD" 2>/dev/null | cut -c1)" == Z ]] && break
  sleep 2; w=$((w+2))
done
grep -q '"appVersion"' "$RESULTS6" 2>/dev/null \
  && ok "cold-start: probe ok" \
  || bad "cold-start: probe missing (log tail: $(tail -3 "$LOG" | tr '\n' '|'))"
# the argv link is queued before the app page shows; it may arrive any time
# after navigation — poll the results file for it
w=0
while (( w < 30 )); do
  grep -q '"protocolLinks".*lxmf://cold123' "$RESULTS6" 2>/dev/null && break
  sleep 0.5; w=$((w+1))
done
if grep -q '"protocolLinks".*lxmf://cold123' "$RESULTS6" 2>/dev/null; then
  ok "cold-start lxmf://cold123 delivered to page: $(grep 'protocolLinks' "$RESULTS6" | tail -1)"
else
  bad "cold-start lxmf://cold123 NOT delivered (results: $(tail -2 "$RESULTS6" | tr '\n' '|'))"
fi
kill_owned_tree; wait "$PID_COLD" 2>/dev/null

echo "== $PASS passed, $FAIL failed =="
[[ $FAIL -eq 0 ]]
