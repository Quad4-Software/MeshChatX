#!/bin/sh
# Start MeshChatX headless on port 8000.

set -eu

mkdir -p /data/meshchatx/config /data/meshchatx/storage

exec /opt/service/meshchatx-venv/bin/meshchatx \
    --host 0.0.0.0 \
    --port 8000 \
    --headless \
    --storage-dir /data/meshchatx/storage \
    --reticulum-config-dir /data/meshchatx/config/.reticulum
