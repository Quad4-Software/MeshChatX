#!/usr/bin/env bash
# Vite HMR (http://127.0.0.1:5173) plus MeshChat backend (HTTPS on MESHCHAT_PORT).
# Vite proxies /api and /ws to https://127.0.0.1:$MESHCHAT_PORT.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Task prefixes every line with [dev] (output: prefixed in Taskfile.yml),
# so log lines here must not add their own [dev] prefix.
if [[ -t 1 ]]; then
    C_RESET=$'\e[0m' C_DIM=$'\e[2m' C_BOLD=$'\e[1m'
    C_CYAN=$'\e[36m' C_GREEN=$'\e[32m' C_YELLOW=$'\e[33m' C_RED=$'\e[31m'
else
    C_RESET='' C_DIM='' C_BOLD='' C_CYAN='' C_GREEN='' C_YELLOW='' C_RED=''
fi

log()  { printf '%s•%s %s\n' "$C_CYAN" "$C_RESET" "$*"; }
ok()   { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s!%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
err()  { printf '%s✗%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
link() { printf '%s%s%s' "$C_BOLD$C_CYAN" "$1" "$C_RESET"; }

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export MESHCHAT_PORT="${MESHCHAT_PORT:-8000}"
export E2E_BACKEND_PORT="$MESHCHAT_PORT"
# Vite proxies /ws with changeOrigin. Trust loopback so X-Forwarded-Host
# (browser :5173) passes the WebSocket Origin check against backend :8000.
export MESHCHAT_TRUSTED_PROXIES="${MESHCHAT_TRUSTED_PROXIES:-127.0.0.1/32}"

BE_PID=""
cleanup() {
    if [[ -n "$BE_PID" ]] && kill -0 "$BE_PID" 2>/dev/null; then
        # TERM first so MeshChat can WAL-checkpoint. Escalate only after a wait.
        kill -TERM "$BE_PID" 2>/dev/null || true
        local waited=0
        while kill -0 "$BE_PID" 2>/dev/null && (( waited < 50 )); do
            sleep 0.1
            waited=$((waited + 1))
        done
        if kill -0 "$BE_PID" 2>/dev/null; then
            warn "Backend still running after TERM wait; sending KILL"
            kill -KILL "$BE_PID" 2>/dev/null || true
        fi
        wait "$BE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

start_backend() {
    local -a cmd
    if [[ "${MESHCHAT_DEBUGPY:-0}" == "1" ]]; then
        local dbg_port="${MESHCHAT_DEBUGPY_PORT:-5678}"
        if ! uv run python -c "import debugpy" >/dev/null 2>&1; then
            err "debugpy is not installed. Run: task deps:backend"
            exit 1
        fi
        cmd=(uv run python -m debugpy --listen "127.0.0.1:${dbg_port}")
        if [[ "${MESHCHAT_DEBUGPY_WAIT:-0}" == "1" ]]; then
            cmd+=(--wait-for-client)
            warn "debugpy waiting for attach on 127.0.0.1:${dbg_port}"
        else
            log "debugpy listening on 127.0.0.1:${dbg_port} (attach Backend: Attach debugpy)"
        fi
        cmd+=(-m meshchatx.meshchat --headless --host 127.0.0.1 --port "$MESHCHAT_PORT")
        "${cmd[@]}" &
    else
        uv run python -m meshchatx.meshchat --headless --host 127.0.0.1 --port "$MESHCHAT_PORT" &
    fi
    BE_PID=$!
}

start_backend

BACKEND_URL="https://127.0.0.1:${MESHCHAT_PORT}/api/v1/status"
BACKEND_WAIT_SECS="${DEV_BACKEND_WAIT:-120}"
BACKEND_POLL_INTERVAL="${DEV_BACKEND_POLL_INTERVAL:-0.5}"
deadline=$((SECONDS + BACKEND_WAIT_SECS))

tcp_connectable() {
    # Returns 0 when a TCP handshake to 127.0.0.1:MESHCHAT_PORT completes.
    python3 - "$MESHCHAT_PORT" <<'PY'
import socket, sys
port = int(sys.argv[1])
try:
    with socket.create_connection(("127.0.0.1", port), timeout=1.0):
        raise SystemExit(0)
except OSError:
    raise SystemExit(1)
PY
}

printf '\n%sMeshChatX dev%s  %sbackend https://127.0.0.1:%s%s\n\n' \
    "$C_BOLD" "$C_RESET" "$C_DIM" "$MESHCHAT_PORT" "$C_RESET"
log "Waiting for backend on port ${MESHCHAT_PORT} ${C_DIM}${BACKEND_URL}${C_RESET}"
saw_listen=0
while (( SECONDS < deadline )); do
    if ! kill -0 "$BE_PID" 2>/dev/null; then
        err "Backend process exited before becoming ready."
        wait "$BE_PID" 2>/dev/null || true
        exit 1
    fi
    if ss -ltn "( sport = :${MESHCHAT_PORT} )" 2>/dev/null | grep -q LISTEN; then
        saw_listen=1
    fi
    # Use /api/v1/status. It is exempt from auth and the still-starting 503 gate
    # so the Vite process can start while deferred network finishes.
    if curl -fsSk --max-time 2 "$BACKEND_URL" >/dev/null 2>&1; then
        ok "Backend ready"
        break
    fi
    sleep "$BACKEND_POLL_INTERVAL"
done

if ! curl -fsSk --max-time 2 "$BACKEND_URL" >/dev/null 2>&1; then
    err "Backend did not respond on ${BACKEND_URL} within ${BACKEND_WAIT_SECS}s."
    if (( saw_listen )) && ! tcp_connectable; then
        err "Port ${MESHCHAT_PORT} is LISTEN but TCP handshakes time out."
        err "Something on this host is blackholing that port (firewall / Netbird / VPN)."
        err "Retry with a free port, for example: MESHCHAT_PORT=8002 task dev"
    fi
    exit 1
fi

VITE_HOST="${VITE_DEV_HOST:-127.0.0.1}"
VITE_PORT="${VITE_DEV_PORT:-5173}"

log "Vite dev server  $(link "http://${VITE_HOST}:${VITE_PORT}")"
log "API proxy        $(link "${BACKEND_URL%/api/v1/status}")"
if [[ "${MESHCHAT_VUE_DEVTOOLS:-1}" != "0" ]]; then
    log "Vue DevTools overlay on ${C_DIM}(MESHCHAT_VUE_DEVTOOLS=0 disables)${C_RESET}"
fi
pnpm run dev -- --host "$VITE_HOST" --port "$VITE_PORT"
