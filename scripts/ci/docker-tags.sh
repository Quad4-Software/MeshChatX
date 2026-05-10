#!/bin/sh
# Generate Docker image tags from git context.
#
# Usage: docker-tags.sh <image_name> [output_file]
# Environment: GITEA_REF / GITHUB_REF, GITEA_REF_NAME / GITHUB_REF_NAME, TAG_SUFFIX
#
# The output file contains one `-t registry/image:tag` per line,
# suitable for passing directly to `docker buildx build`.
set -eu

IMAGE="$1"
OUTPUT="${2:-/tmp/docker-tags.txt}"
SUFFIX="${TAG_SUFFIX:-}"
: > "$OUTPUT"

_suffix_tag() {
    local tag="$1"
    if [ -n "$SUFFIX" ]; then
        printf '%s' "${tag}${SUFFIX}"
    else
        printf '%s' "$tag"
    fi
}

SHA="$(git rev-parse --short HEAD)"
REF="${GITEA_REF:-${GITHUB_REF:-}}"
BRANCH="${GITEA_REF_NAME:-${GITHUB_REF_NAME:-$(git rev-parse --abbrev-ref HEAD)}}"

echo "-t ${IMAGE}:$(_suffix_tag "sha-${SHA}")" >> "$OUTPUT"

case "$BRANCH" in
    master|main)
        echo "-t ${IMAGE}:$(_suffix_tag "latest")" >> "$OUTPUT"
        ;;
    dev)
        echo "-t ${IMAGE}:$(_suffix_tag "dev")" >> "$OUTPUT"
        ;;
esac

case "$REF" in
    refs/tags/v*)
        VERSION="${REF#refs/tags/v}"
        echo "-t ${IMAGE}:$(_suffix_tag "latest")" >> "$OUTPUT"
        echo "-t ${IMAGE}:$(_suffix_tag "${VERSION}")" >> "$OUTPUT"
        echo "-t ${IMAGE}:$(_suffix_tag "v${VERSION}")" >> "$OUTPUT"
        MAJOR_MINOR="$(echo "$VERSION" | cut -d. -f1-2)"
        if [ "$MAJOR_MINOR" != "$VERSION" ]; then
            echo "-t ${IMAGE}:$(_suffix_tag "${MAJOR_MINOR}")" >> "$OUTPUT"
            echo "-t ${IMAGE}:$(_suffix_tag "v${MAJOR_MINOR}")" >> "$OUTPUT"
        fi
        ;;
    refs/tags/*)
        TAG="${REF#refs/tags/}"
        echo "-t ${IMAGE}:$(_suffix_tag "latest")" >> "$OUTPUT"
        echo "-t ${IMAGE}:$(_suffix_tag "${TAG}")" >> "$OUTPUT"
        ;;
esac

echo "Generated tags:"
cat "$OUTPUT"
