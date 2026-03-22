#!/bin/sh
# Set up QEMU and Docker Buildx for multi-platform builds.
# Optionally log in to a container registry.
#
# Usage: setup-docker.sh [registry] [username] [password]
#   or set REGISTRY, REGISTRY_USERNAME, REGISTRY_PASSWORD env vars.
set -eu

REGISTRY="${1:-${REGISTRY:-}}"
USERNAME="${2:-${REGISTRY_USERNAME:-}}"
PASSWORD="${3:-${REGISTRY_PASSWORD:-}}"

echo "Registering QEMU binfmt handlers"
sudo apt-get update -qq
sudo apt-get install -y -qq qemu-user-static binfmt-support

echo "Creating Docker Buildx builder"
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap

if [ -n "$REGISTRY" ] && [ -n "$USERNAME" ] && [ -n "$PASSWORD" ]; then
    echo "Logging in to ${REGISTRY}"
    echo "$PASSWORD" | docker login "$REGISTRY" -u "$USERNAME" --password-stdin
fi
