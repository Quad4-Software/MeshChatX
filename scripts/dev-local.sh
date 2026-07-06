#!/usr/bin/env bash
# Vite dev server (HMR) + MeshChat Python backend. Open http://localhost:5173 (or VITE_DEV_PORT).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export MESHCHAT_PORT="${MESHCHAT_PORT:-8000}"
export E2E_BACKEND_PORT="$MESHCHAT_PORT"

BE_PID=""
cleanup() {
    if [[ -n "$BE_PID" ]] && kill -0 "$BE_PID" 2>/dev/null; then
        kill "$BE_PID" 2>/dev/null || true
        wait "$BE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

uv run python -m meshchatx.meshchat --headless --host 127.0.0.1 --port "$MESHCHAT_PORT" &
BE_PID=$!

BACKEND_URL="https://127.0.0.1:${MESHCHAT_PORT}/api/v1/app/info"
BACKEND_WAIT_SECS="${DEV_BACKEND_WAIT:-120}"
BACKEND_POLL_INTERVAL="${DEV_BACKEND_POLL_INTERVAL:-0.5}"
deadline=$((SECONDS + BACKEND_WAIT_SECS))

echo "[dev] Waiting for backend (HTTPS) on port ${MESHCHAT_PORT}..."
while (( SECONDS < deadline )); do
    if ! kill -0 "$BE_PID" 2>/dev/null; then
        echo "[dev] Backend process exited before becoming ready." >&2
        wait "$BE_PID" 2>/dev/null || true
        exit 1
    fi
    if curl -fsSk --max-time 2 "$BACKEND_URL" >/dev/null 2>&1; then
        echo "[dev] Backend ready."
        break
    fi
    sleep "$BACKEND_POLL_INTERVAL"
done

if ! curl -fsSk --max-time 2 "$BACKEND_URL" >/dev/null 2>&1; then
    echo "[dev] Backend did not respond on ${BACKEND_URL} within ${BACKEND_WAIT_SECS}s." >&2
    exit 1
fi

VITE_HOST="${VITE_DEV_HOST:-127.0.0.1}"
VITE_PORT="${VITE_DEV_PORT:-5173}"

pnpm run dev -- --host "$VITE_HOST" --port "$VITE_PORT"
