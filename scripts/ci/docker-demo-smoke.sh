#!/usr/bin/env bash
# Smoke-test docker-compose.demo.yml (Coolify-shaped demo stack).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

IMAGE="${MESHCHAT_DOCKER_DEMO_IMAGE:-reticulum-meshchatx:local}"
COMPOSE_FILE="docker-compose.demo.yml"
OVERRIDE_FILE="${TMPDIR:-/tmp}/meshchatx-demo-smoke-ports.yml"
KEY="${MESHCHAT_ALTCHA_HMAC_KEY:-demo-smoke-hmac-key-change-me}"

STATUS_JSON="${TMPDIR:-/tmp}/meshchatx-demo-smoke-status.json"
cleanup() {
    MESHCHAT_IMAGE="$IMAGE" MESHCHAT_ALTCHA_HMAC_KEY="$KEY" \
        docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" down >/dev/null 2>&1 || true
    rm -f "$OVERRIDE_FILE" "$STATUS_JSON"
}
trap cleanup EXIT

cat >"$OVERRIDE_FILE" <<'EOF'
services:
    meshchatx:
        ports:
            - 127.0.0.1:8000:8000
EOF

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Building $IMAGE..."
    docker build -f Dockerfile -t "$IMAGE" .
fi

MESHCHAT_IMAGE="$IMAGE" MESHCHAT_ALTCHA_HMAC_KEY="$KEY" \
    docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" up -d --pull never

demo_status_ready() {
    curl -fsS -o "$STATUS_JSON" "http://127.0.0.1:8000/api/v1/status" 2>/dev/null || return 1
    python3 -c '
import json,sys
d=json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if d.get("demo_mode") and d.get("altcha_enabled") else 1)
' "$STATUS_JSON"
}

deadline=$((SECONDS + 180))
while [ "$SECONDS" -lt "$deadline" ]; do
    if demo_status_ready; then
        break
    fi
    sleep 3
done

curl -fsS -o "$STATUS_JSON" "http://127.0.0.1:8000/api/v1/status"
python3 -c '
import json,sys
d=json.load(open(sys.argv[1], encoding="utf-8"))
assert d.get("demo_mode") is True
assert d.get("altcha_enabled") is True
print("demo status ok", d.get("status"))
' "$STATUS_JSON"

code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "{}" \
    "http://127.0.0.1:8000/api/v1/lxmf-messages/send")
test "$code" = "403"

echo "Docker demo smoke passed"
