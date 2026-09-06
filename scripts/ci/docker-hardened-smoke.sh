#!/usr/bin/env bash
# Build the standard image and verify hardened docker compose stacks and docker run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

IMAGE="${MESHCHAT_DOCKER_SMOKE_IMAGE:-reticulum-meshchatx:local}"
RUN_CONTAINER="${MESHCHAT_DOCKER_RUN_SMOKE_CONTAINER:-meshchatx-hardened-run-test}"
RUN_PORT="${MESHCHAT_DOCKER_RUN_SMOKE_PORT:-18081}"
TIMEOUT_SEC="${MESHCHAT_DOCKER_SMOKE_TIMEOUT:-180}"
CONFIG_DIR="${MESHCHAT_DOCKER_SMOKE_CONFIG:-$(mktemp -d)}"

cleanup() {
    docker compose -f docker/docker-compose.yml down >/dev/null 2>&1 || true
    docker compose -f docker/docker-compose.dev.yml down >/dev/null 2>&1 || true
    docker compose -f docker/docker-compose.coolify.yml down >/dev/null 2>&1 || true
    docker rm -f "$RUN_CONTAINER" >/dev/null 2>&1 || true
    if [ "${MESHCHAT_DOCKER_SMOKE_KEEP_CONFIG:-0}" != "1" ] && [ -n "${TMP_CONFIG_CREATED:-}" ]; then
        rm -rf "$CONFIG_DIR"
    fi
}
trap cleanup EXIT

if [ -z "${MESHCHAT_DOCKER_SMOKE_CONFIG:-}" ]; then
    TMP_CONFIG_CREATED=1
fi
chmod 777 "$CONFIG_DIR"

wait_https() {
    local port="$1"
    local deadline=$((SECONDS + TIMEOUT_SEC))
    while [ "$SECONDS" -lt "$deadline" ]; do
        if out=$(curl -fsSk "https://127.0.0.1:${port}/api/v1/status" 2>/dev/null) &&
            printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" else 1)'; then
            echo "$out"
            return 0
        fi
        sleep 3
    done
    return 1
}

wait_container_healthy() {
    local name="$1"
    local deadline=$((SECONDS + TIMEOUT_SEC))
    local state=""
    while [ "$SECONDS" -lt "$deadline" ]; do
        state=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo missing)
        if [ "$state" = "healthy" ]; then
            return 0
        fi
        if [ "$state" = "unhealthy" ]; then
            docker logs "$name" >&2 || true
            return 1
        fi
        sleep 3
    done
    echo "Timed out waiting for container health (last state: ${state})" >&2
    docker logs "$name" >&2 || true
    return 1
}

echo "Building Docker image ${IMAGE}..."
docker build -f docker/Dockerfile -t "$IMAGE" .

echo "=== docker/docker-compose.yml (hardened) ==="
MESHCHAT_IMAGE="$IMAGE" docker compose -f docker/docker-compose.yml up -d --pull never
wait_container_healthy reticulum-meshchatx
wait_https 8000 >/dev/null
docker compose -f docker/docker-compose.yml down

echo "=== docker/docker-compose.dev.yml (hardened) ==="
docker compose -f docker/docker-compose.dev.yml up -d --pull never
wait_container_healthy reticulum-meshchatx
wait_https 8000 >/dev/null
docker compose -f docker/docker-compose.dev.yml down

echo "=== docker/docker-compose.coolify.yml (hardened) ==="
MESHCHAT_IMAGE="$IMAGE" docker compose -f docker/docker-compose.coolify.yml up -d --pull never
coolify_cid=$(docker compose -f docker/docker-compose.coolify.yml ps -q meshchatx)
wait_container_healthy "$coolify_cid"
docker exec "$coolify_cid" python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/status').read().decode())" >/dev/null
docker compose -f docker/docker-compose.coolify.yml down

echo "=== docker run (hardened) ==="
docker run -d --name "$RUN_CONTAINER" \
    --restart unless-stopped \
    --init \
    --user 1000:1000 \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --read-only \
    --tmpfs /tmp:noexec,nosuid,size=256m \
    --tmpfs /home/meshchat:nosuid,size=64m \
    --cpus=2.0 \
    --memory=1g \
    --memory-reservation=256m \
    --pids-limit=512 \
    -p "127.0.0.1:${RUN_PORT}:8000" \
    -v "${CONFIG_DIR}:/config" \
    "$IMAGE" >/dev/null

status_json=$(wait_https "$RUN_PORT")
echo "Docker hardened smoke passed: ${status_json}"
