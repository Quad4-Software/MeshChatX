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
# Chaos proxy: peer connects here, proxy forwards to E2E_PEER_PORT. Specs
# inject link faults through a control file in the share dir.
export E2E_CHAOS_PORT="${E2E_CHAOS_PORT:-43837}"
export E2E_CHAOS_CONTROL="${E2E_PEER_SHARE:-/tmp/meshchatx-e2e-peer-share}/chaos.mode"
export E2E_PEER2_SHARE="${E2E_PEER2_SHARE:-/tmp/meshchatx-e2e-peer2-share}"
E2E_LIVE_MESH="${E2E_LIVE_MESH:-1}"
E2E_LIVE_MESH2="${E2E_LIVE_MESH2:-1}"
rm -rf "$E2E_PEER_SHARE" "$E2E_PEER2_SHARE"
mkdir -p "$E2E_PEER_SHARE" "$E2E_PEER2_SHARE"

# Free the e2e ports from leftovers of earlier interrupted runs. An
# orphaned backend on the backend port would otherwise let health checks
# pass against the wrong process and pollute assertions.
free_port() {
    local port="$1"
    local pids
    pids="$(ss -tlnp "sport = :${port}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true)"
    if [[ -z "$pids" ]]; then
        return 0
    fi
    echo "E2E: freeing port ${port} (pids: $(echo $pids | tr '\n' ' '))"
    echo "$pids" | xargs -r kill 2>/dev/null || true
    for _ in $(seq 1 10); do
        pids="$(ss -tlnp "sport = :${port}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true)"
        [[ -z "$pids" ]] && return 0
        sleep 0.5
    done
    pids="$(ss -tlnp "sport = :${port}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true)"
    if [[ -n "$pids" ]]; then
        echo "E2E: forcing port ${port} free"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
    if ss -tln "sport = :${port}" | grep -q "LISTEN"; then
        echo "E2E: port ${port} still bound after SIGKILL - refusing to start on a polluted socket" >&2
        exit 1
    fi
}

for port in "${BACKEND_PORT}" "${E2E_PEER_PORT}" "${E2E_CHAOS_PORT}" "${VITE_PORT}"; do
    free_port "$port"
done

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
    if [[ -n "${VITE_PID:-}" ]] && kill -0 "$VITE_PID" 2>/dev/null; then
        kill "$VITE_PID" 2>/dev/null || true
        wait "$VITE_PID" 2>/dev/null || true
    fi
    if [[ -n "${PEER2_PID:-}" ]] && kill -0 "$PEER2_PID" 2>/dev/null; then
        kill "$PEER2_PID" 2>/dev/null || true
        wait "$PEER2_PID" 2>/dev/null || true
    fi
    if [[ -n "${PEER_PID:-}" ]] && kill -0 "$PEER_PID" 2>/dev/null; then
        kill "$PEER_PID" 2>/dev/null || true
        wait "$PEER_PID" 2>/dev/null || true
    fi
    if [[ -n "${CHAOS_PID:-}" ]] && kill -0 "$CHAOS_PID" 2>/dev/null; then
        kill "$CHAOS_PID" 2>/dev/null || true
        wait "$CHAOS_PID" 2>/dev/null || true
    fi
    local_bpid="${BACK_PID:-}"
    if [[ -f "$TMPDIR/backend.pid" ]]; then
        local_bpid="$(cat "$TMPDIR/backend.pid")"
    fi
    if [[ -n "$local_bpid" ]] && kill -0 "$local_bpid" 2>/dev/null; then
        kill "$local_bpid" 2>/dev/null || true
        wait "$local_bpid" 2>/dev/null || true
    fi
    rm -rf "$TMPDIR"
    rm -rf "$E2E_PEER_SHARE" "$E2E_PEER2_SHARE"
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
echo "$BACK_PID" > "$TMPDIR/backend.pid"
cat > "${E2E_PEER_SHARE}/stack_meta.json" <<META
{
  "backend_port": ${BACKEND_PORT},
  "backend_pid_file": "${TMPDIR}/backend.pid",
  "backend_storage": "${TMPDIR}/storage",
  "backend_rns": "${TMPDIR}/rns",
  "chaos_port": ${E2E_CHAOS_PORT},
  "chaos_control": "${E2E_PEER_SHARE}/chaos.mode",
  "tmp_root": "${TMPDIR}"
}
META

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
    # A killed earlier run's cleanup trap can delete the share dir after
    # our initial mkdir; recreate it just before use.
    mkdir -p "$E2E_PEER_SHARE" "$E2E_PEER2_SHARE"
    echo "E2E: starting chaos proxy :${E2E_CHAOS_PORT} -> :${E2E_PEER_PORT}"
    echo pass > "${E2E_PEER_SHARE}/chaos.mode"
    uv run python "$ROOT/scripts/e2e/chaos-proxy.py"         "${E2E_CHAOS_PORT}" "${E2E_PEER_PORT}" "${E2E_PEER_SHARE}/chaos.mode" &
    CHAOS_PID=$!
    echo "E2E: starting live mesh peer (TCPClient :${E2E_CHAOS_PORT} via proxy)"
    uv run python "$ROOT/scripts/e2e/live-peer.py"         "$TMPDIR/peer-rns" "${E2E_CHAOS_PORT}" "$E2E_PEER_SHARE" &
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

    if [[ "$E2E_LIVE_MESH2" == "1" ]]; then
        echo "E2E: starting second live mesh peer (TCPClient :${E2E_CHAOS_PORT} via proxy)"
        uv run python "$ROOT/scripts/e2e/live-peer.py"             "$TMPDIR/peer2-rns" "${E2E_CHAOS_PORT}" "$E2E_PEER2_SHARE" &
        PEER2_PID=$!
        for i in $(seq 1 90); do
            if [[ -f "${E2E_PEER2_SHARE}/peer_ready.json" ]]; then
                echo "E2E: second peer ready after ${i}s"
                break
            fi
            if ! kill -0 "$PEER2_PID" 2>/dev/null; then
                echo "E2E: second live peer exited early"
                break
            fi
            sleep 1
        done
    fi
fi

echo "E2E: starting Vite on ${VITE_HOST}:${VITE_PORT}"
# Vue DevTools overlay intercepts clicks and is not part of the product UI.
export MESHCHAT_VUE_DEVTOOLS=0
pnpm exec vite --host "${VITE_HOST}" --port "${VITE_PORT}" &
VITE_PID=$!
wait "$VITE_PID"
