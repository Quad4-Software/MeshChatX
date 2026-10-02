#!/bin/sh
# Install MeshChatX inside the Alpine guest.

set -eu

mkdir -p /data/meshchatx/config /data/meshchatx/storage /opt/service

# Install from PyPI — use a venv to keep the system python clean
python3 -m venv /opt/service/meshchatx-venv
/opt/service/meshchatx-venv/bin/pip install --quiet reticulum-meshchatx

ln -sfn /opt/service/meshchatx-venv/bin/meshchatx /usr/local/bin/meshchatx
echo "meshchatx installed: $(/opt/service/meshchatx-venv/bin/meshchatx --version 2>&1 || echo 'ok')"
