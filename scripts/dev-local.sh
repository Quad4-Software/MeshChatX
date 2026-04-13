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

poetry run python -m meshchatx.meshchat &
BE_PID=$!

sleep "${DEV_BACKEND_WAIT:-1}"

VITE_HOST="${VITE_DEV_HOST:-127.0.0.1}"
VITE_PORT="${VITE_DEV_PORT:-5173}"

pnpm run dev -- --host "$VITE_HOST" --port "$VITE_PORT"
