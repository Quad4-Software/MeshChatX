#!/usr/bin/env bash
# Fail unless the given SHA has a successful CI workflow run (workflow file ci.yml).
# Usage: github-require-ci-green.sh <sha>
set -euo pipefail

SHA="${1:?sha required}"

if ! command -v gh >/dev/null 2>&1; then
    echo "gh is required" >&2
    exit 1
fi
if [ -z "${GH_TOKEN:-}" ]; then
    echo "GH_TOKEN is required" >&2
    exit 1
fi

# Prefer completed success on this exact commit.
conclusion="$(
    gh run list --workflow ci.yml --commit "$SHA" --limit 20 --json conclusion,status,headSha \
        --jq "[.[] | select(.headSha == \"${SHA}\" and .status == \"completed\")] | map(.conclusion) | unique | join(\",\")"
)"

if [[ ",${conclusion}," == *",success,"* ]]; then
    echo "CI green on ${SHA} (conclusions: ${conclusion})"
    exit 0
fi

echo "CI is not green on ${SHA} (conclusions: ${conclusion:-none}). Refusing to cut release." >&2
exit 1
