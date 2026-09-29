#!/usr/bin/env bash
# Restart the e2e backend in place, preserving storage and RNS config.
# Used by specs that assert reconnect-after-restart behavior.
set -euo pipefail

META="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PID_FILE="$(python3 -c "import json;print(json.load(open('$META'))['backend_pid_file'])")"
STORAGE="$(python3 -c "import json;print(json.load(open('$META'))['backend_storage'])")"
RNSDIR="$(python3 -c "import json;print(json.load(open('$META'))['backend_rns'])")"
PORT="$(python3 -c "import json;print(json.load(open('$META'))['backend_port'])")"
TMP_ROOT="$(python3 -c "import json;print(json.load(open('$META'))['tmp_root'])")"

OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" 2>/dev/null || true
    for _ in $(seq 1 60); do
        kill -0 "$OLD_PID" 2>/dev/null || break
        sleep 0.5
    done
    kill -9 "$OLD_PID" 2>/dev/null || true
fi

export MESHCHAT_NO_HTTPS=1
export MESHCHAT_TRUSTED_PROXIES="${MESHCHAT_TRUSTED_PROXIES:-127.0.0.1/32}"
export MESHCHAT_LANDLOCK=0
export MESHCHAT_LOG_DIR="$TMP_ROOT/logs"

uv run python -m meshchatx.meshchat \
    --headless \
    --no-https \
    --host 127.0.0.1 \
    --port "$PORT" \
    --storage-dir "$STORAGE" \
    --reticulum-config-dir "$RNSDIR" \
    >> "$TMP_ROOT/logs/meshchatx.log" 2>&1 &
echo $! > "$PID_FILE"

for i in $(seq 1 240); do
    if body="$(curl -sf "http://127.0.0.1:${PORT}/api/v1/status" 2>/dev/null)"; then
        if printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" or d.get("network_ready") else 1)'; then
            echo "backend restarted, ready after ${i}s"
            exit 0
        fi
    fi
    if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "backend exited during restart" >&2
        exit 1
    fi
    sleep 1
done
echo "backend did not become ready in time" >&2
exit 1
