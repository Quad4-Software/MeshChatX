#!/bin/sh
# Generate Docker image tags from git context.
#
# Usage: docker-tags.sh <image_name> [output_file]
# Environment: GITEA_REF / GITHUB_REF, GITEA_REF_NAME / GITHUB_REF_NAME
#
# The output file contains one `-t registry/image:tag` per line,
# suitable for passing directly to `docker buildx build`.
set -eu

IMAGE="$1"
OUTPUT="${2:-/tmp/docker-tags.txt}"
: > "$OUTPUT"

SHA="$(git rev-parse --short HEAD)"
REF="${GITEA_REF:-${GITHUB_REF:-}}"
BRANCH="${GITEA_REF_NAME:-${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD)}}"

echo "-t ${IMAGE}:sha-${SHA}" >> "$OUTPUT"

case "$BRANCH" in
    master|main)
        echo "-t ${IMAGE}:latest" >> "$OUTPUT"
        ;;
    dev)
        echo "-t ${IMAGE}:dev" >> "$OUTPUT"
        ;;
esac

case "$REF" in
    refs/tags/v*)
        VERSION="${REF#refs/tags/v}"
        echo "-t ${IMAGE}:${VERSION}" >> "$OUTPUT"
        echo "-t ${IMAGE}:v${VERSION}" >> "$OUTPUT"
        MAJOR_MINOR="$(echo "$VERSION" | cut -d. -f1-2)"
        if [ "$MAJOR_MINOR" != "$VERSION" ]; then
            echo "-t ${IMAGE}:${MAJOR_MINOR}" >> "$OUTPUT"
            echo "-t ${IMAGE}:v${MAJOR_MINOR}" >> "$OUTPUT"
        fi
        ;;
    refs/tags/*)
        TAG="${REF#refs/tags/}"
        echo "-t ${IMAGE}:${TAG}" >> "$OUTPUT"
        ;;
esac

echo "Generated tags:"
cat "$OUTPUT"
