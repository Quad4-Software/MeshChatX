#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-18079}"
export MESHCHAT_NO_HTTPS=1
# Vite proxies /ws with changeOrigin. Trust loopback so X-Forwarded-Host
# (browser Vite port) passes the WebSocket Origin check.
export MESHCHAT_TRUSTED_PROXIES="${MESHCHAT_TRUSTED_PROXIES:-127.0.0.1/32}"
# E2E exercises /api/v1/self-test (subprocess + bots). Keep Landlock off so
# uv-managed interpreters and temp paths are not a sandbox variable.
export MESHCHAT_LANDLOCK=0
BACKEND_PORT="$E2E_BACKEND_PORT"
VITE_HOST="${E2E_VITE_HOST:-127.0.0.1}"
VITE_PORT="${E2E_VITE_PORT:-5173}"

TMPDIR="$(mktemp -d -t meshchat-e2e-XXXXXX)"
export MESHCHAT_LOG_DIR="$TMPDIR/logs"
mkdir -p "$MESHCHAT_LOG_DIR"

# Live-mesh peer: backend gets a TCPServerInterface; the peer subprocess
# links in as a TCP client and runs lxmf.delivery plus an RRC hub. Specs
# coordinate through E2E_PEER_SHARE files. Skip with E2E_LIVE_MESH=0.
# Fixed default so the Playwright spec process can find it without env.
export E2E_PEER_SHARE="${E2E_PEER_SHARE:-/tmp/meshchatx-e2e-peer-share}"
export E2E_PEER_PORT="${E2E_PEER_PORT:-43737}"
E2E_LIVE_MESH="${E2E_LIVE_MESH:-1}"
rm -rf "$E2E_PEER_SHARE"
mkdir -p "$E2E_PEER_SHARE"

if [[ "$E2E_LIVE_MESH" == "1" ]]; then
    mkdir -p "$TMPDIR/rns"
    cat > "$TMPDIR/rns/config" <<CFG
[reticulum]
  enable_transport = False
  share_instance = No
  panic_on_interface_error = No

[interfaces]
  [[E2E Listener]]
    type = TCPServerInterface
    enabled = Yes
    listen_ip = 127.0.0.1
    listen_port = ${E2E_PEER_PORT}
CFG
fi

cleanup() {
    if [[ -n "${PEER_PID:-}" ]] && kill -0 "$PEER_PID" 2>/dev/null; then
        kill "$PEER_PID" 2>/dev/null || true
        wait "$PEER_PID" 2>/dev/null || true
    fi
    if [[ -n "${BACK_PID:-}" ]] && kill -0 "$BACK_PID" 2>/dev/null; then
        kill "$BACK_PID" 2>/dev/null || true
        wait "$BACK_PID" 2>/dev/null || true
    fi
    rm -rf "$TMPDIR"
    rm -rf "$E2E_PEER_SHARE"
}

trap cleanup EXIT INT TERM

echo "E2E: starting MeshChat backend on 127.0.0.1:${BACKEND_PORT} (isolated storage under ${TMPDIR})"

uv run python -m meshchatx.meshchat \
    --headless \
    --no-https \
    --host 127.0.0.1 \
    --port "${BACKEND_PORT}" \
    --storage-dir "$TMPDIR/storage" \
    --reticulum-config-dir "$TMPDIR/rns" \
    &
BACK_PID=$!

echo "E2E: waiting for /api/v1/status network_ready..."
ready=0
for i in $(seq 1 240); do
    if ! kill -0 "$BACK_PID" 2>/dev/null; then
        echo "E2E: backend process exited before becoming ready"
        exit 1
    fi
    if body="$(curl -sf "http://127.0.0.1:${BACKEND_PORT}/api/v1/status" 2>/dev/null)"; then
        if printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" or d.get("network_ready") else 1)'; then
            ready=1
            echo "E2E: backend ready after ${i}s"
            break
        fi
    fi
    sleep 1
done

if [[ "$ready" -ne 1 ]]; then
    echo "E2E: backend did not respond on :${BACKEND_PORT} within 240s"
    exit 1
fi

if [[ "$E2E_LIVE_MESH" == "1" ]]; then
    echo "E2E: starting live mesh peer (TCPClient :${E2E_PEER_PORT})"
    uv run python "$ROOT/scripts/e2e/live-peer.py"         "$TMPDIR/peer-rns" "${E2E_PEER_PORT}" "$E2E_PEER_SHARE" &
    PEER_PID=$!
    peer_ready=0
    for i in $(seq 1 90); do
        if [[ -f "${E2E_PEER_SHARE}/peer_ready.json" ]]; then
            peer_ready=1
            echo "E2E: live peer ready after ${i}s"
            break
        fi
        if ! kill -0 "$PEER_PID" 2>/dev/null; then
            echo "E2E: live peer exited early"
            break
        fi
        sleep 1
    done
    if [[ "$peer_ready" -ne 1 ]]; then
        echo "E2E: live peer not ready; live-mesh specs will skip"
    fi
fi

echo "E2E: starting Vite on ${VITE_HOST}:${VITE_PORT}"
# Vue DevTools overlay intercepts clicks and is not part of the product UI.
export MESHCHAT_VUE_DEVTOOLS=0
pnpm exec vite --host "${VITE_HOST}" --port "${VITE_PORT}" &
VITE_PID=$!
wait "$VITE_PID"
