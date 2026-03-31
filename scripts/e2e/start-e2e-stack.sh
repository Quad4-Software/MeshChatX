#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${E2E_BACKEND_PORT:-8000}"
VITE_HOST="${E2E_VITE_HOST:-127.0.0.1}"
VITE_PORT="${E2E_VITE_PORT:-5173}"

TMPDIR="$(mktemp -d -t meshchat-e2e-XXXXXX)"
export MESHCHAT_LOG_DIR="$TMPDIR/logs"
mkdir -p "$MESHCHAT_LOG_DIR"

cleanup() {
    if [[ -n "${BACK_PID:-}" ]] && kill -0 "$BACK_PID" 2>/dev/null; then
        kill "$BACK_PID" 2>/dev/null || true
        wait "$BACK_PID" 2>/dev/null || true
    fi
    rm -rf "$TMPDIR"
}

trap cleanup EXIT INT TERM

echo "E2E: starting MeshChat backend on 127.0.0.1:${BACKEND_PORT} (isolated storage under ${TMPDIR})"

poetry run python -m meshchatx.meshchat \
    --headless \
    --no-https \
    --host 127.0.0.1 \
    --port "${BACKEND_PORT}" \
    --storage-dir "$TMPDIR/storage" \
    --reticulum-config-dir "$TMPDIR/rns" \
    &
BACK_PID=$!

echo "E2E: waiting for /api/v1/status (HTTP 200)..."
ready=0
for i in $(seq 1 240); do
    if ! kill -0 "$BACK_PID" 2>/dev/null; then
        echo "E2E: backend process exited before becoming ready"
        exit 1
    fi
    if curl -sf "http://127.0.0.1:${BACKEND_PORT}/api/v1/status" >/dev/null 2>&1; then
        ready=1
        echo "E2E: backend ready after ${i}s"
        break
    fi
    sleep 1
done

if [[ "$ready" -ne 1 ]]; then
    echo "E2E: backend did not respond on :${BACKEND_PORT} within 240s"
    exit 1
fi

echo "E2E: starting Vite on ${VITE_HOST}:${VITE_PORT}"
pnpm exec vite --host "${VITE_HOST}" --port "${VITE_PORT}" &
VITE_PID=$!
wait "$VITE_PID"
