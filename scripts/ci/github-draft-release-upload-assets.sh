#!/usr/bin/env bash
# Create the GitHub release as a draft if missing, then upload every file in DIR to that tag.
# Requires: gh, GH_TOKEN. TAG from TAG or GITHUB_REF_NAME.
set -euo pipefail

DIR="${1:?path to directory of files to upload}"
TAG="${TAG:-${GITHUB_REF_NAME:?set TAG or GITHUB_REF_NAME}}"

if ! command -v gh >/dev/null 2>&1; then
    echo "gh is required" >&2
    exit 1
fi

if [ -z "${GH_TOKEN:-}" ]; then
    echo "GH_TOKEN is required" >&2
    exit 1
fi

export GH_TOKEN

if [ -z "${GH_REPO:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    export GH_REPO="$GITHUB_REPOSITORY"
fi

if ! gh release view "$TAG" >/dev/null 2>&1; then
    gh release create "$TAG" --draft --title "$TAG" --notes "Automated draft release. Review assets and provenance before publishing."
fi

mapfile -t files < <(find "$DIR" -type f)
if [ "${#files[@]}" -eq 0 ]; then
    echo "No files under ${DIR}" >&2
    exit 1
fi

gh release upload "$TAG" "${files[@]}" --clobber
