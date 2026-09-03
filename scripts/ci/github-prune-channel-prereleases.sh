#!/usr/bin/env bash
# Prune old Testing/Beta GitHub prereleases. Never deletes Stable (non-prerelease).
# Env: GH_TOKEN, MESHCHATX_KEEP_TESTING (default 7), MESHCHATX_KEEP_BETA (default 5)
set -euo pipefail

KEEP_TESTING="${MESHCHATX_KEEP_TESTING:-7}"
KEEP_BETA="${MESHCHATX_KEEP_BETA:-5}"

if ! command -v gh >/dev/null 2>&1; then
    echo "gh is required" >&2
    exit 1
fi
if [ -z "${GH_TOKEN:-}" ]; then
    echo "GH_TOKEN is required" >&2
    exit 1
fi

prune_prefix() {
    local prefix="$1"
    local keep="$2"
    local tags
    mapfile -t tags < <(
        gh release list --limit 200 --json tagName,isPrerelease,createdAt \
            --jq "[.[] | select(.isPrerelease) | select(.tagName | startswith(\"${prefix}\"))] | sort_by(.createdAt) | reverse | .[].tagName"
    )
    if [ "${#tags[@]}" -le "$keep" ]; then
        echo "Keep ${#tags[@]} ${prefix}* prereleases (limit ${keep})"
        return 0
    fi
    local i
    for ((i = keep; i < ${#tags[@]}; i++)); do
        local tag="${tags[$i]}"
        echo "Deleting old prerelease ${tag}"
        gh release delete "$tag" --yes --cleanup-tag || true
    done
}

prune_prefix "nightly-" "$KEEP_TESTING"
prune_prefix "testing-" "$KEEP_TESTING"
prune_prefix "beta-" "$KEEP_BETA"
prune_prefix "preview-" "$KEEP_BETA"

echo "Prune complete"
