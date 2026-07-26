#!/usr/bin/env bash
# Build the standard Docker image and verify /api/v1/status over HTTPS inside the container.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

IMAGE="${MESHCHAT_DOCKER_SMOKE_IMAGE:-meshchatx-runtime-smoke:local}"
CONTAINER="${MESHCHAT_DOCKER_SMOKE_CONTAINER:-meshchatx-runtime-smoke}"
HOST_PORT="${MESHCHAT_DOCKER_SMOKE_PORT:-18080}"
CONFIG_DIR="${MESHCHAT_DOCKER_SMOKE_CONFIG:-$(mktemp -d)}"
TIMEOUT_SEC="${MESHCHAT_DOCKER_SMOKE_TIMEOUT:-180}"

cleanup() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    if [ "${MESHCHAT_DOCKER_SMOKE_KEEP_CONFIG:-0}" != "1" ] && [ -n "${TMP_CONFIG_CREATED:-}" ]; then
        rm -rf "$CONFIG_DIR"
    fi
}
trap cleanup EXIT

if [ "$CONFIG_DIR" = "$(mktemp -u)" ] || [ ! -d "$CONFIG_DIR" ]; then
    :
fi
if [ -z "${MESHCHAT_DOCKER_SMOKE_CONFIG:-}" ]; then
    TMP_CONFIG_CREATED=1
fi

echo "Building Docker image ${IMAGE}..."
docker build -f Dockerfile -t "$IMAGE" .

cleanup
mkdir -p "$CONFIG_DIR"

echo "Starting container on host port ${HOST_PORT}..."
docker run -d \
    --name "$CONTAINER" \
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
    -p "127.0.0.1:${HOST_PORT}:8000" \
    -v "${CONFIG_DIR}:/config" \
    "$IMAGE" >/dev/null

deadline=$((SECONDS + TIMEOUT_SEC))
status_ok=0
while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsSk "https://127.0.0.1:${HOST_PORT}/api/v1/status" >/tmp/meshchatx-docker-status.json 2>/dev/null; then
        if python3 -c 'import json,sys; d=json.load(open("/tmp/meshchatx-docker-status.json")); sys.exit(0 if d.get("status")=="ok" else 1)'; then
            status_ok=1
            break
        fi
    fi
    if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
        echo "Container exited early. Logs:" >&2
        docker logs "$CONTAINER" >&2 || true
        exit 1
    fi
    sleep 2
done

if [ "$status_ok" != "1" ]; then
    echo "Timed out waiting for https://127.0.0.1:${HOST_PORT}/api/v1/status" >&2
    docker logs "$CONTAINER" >&2 || true
    exit 1
fi

echo "Docker runtime smoke passed: $(cat /tmp/meshchatx-docker-status.json)"
