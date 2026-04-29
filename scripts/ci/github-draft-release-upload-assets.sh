#!/usr/bin/env bash
# Create the GitHub release as a draft if missing, then upload every file in DIR to that tag.
# Skips electron-builder builder-debug.yml (and cosign bundles), including collision-renamed
# copies (e.g. win__builder-debug.yml). Requires: gh, GH_TOKEN. TAG from TAG or GITHUB_REF_NAME.
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

mapfile -d '' -t all < <(find "$DIR" -type f -print0)

skip_noise() {
    local base="$1"
    case "$base" in
        builder-debug.yml | builder-debug.yml.cosign.bundle) return 0 ;;
        *__builder-debug.yml | *__builder-debug.yml.cosign.bundle) return 0 ;;
    esac
    return 1
}

filtered=()
for f in "${all[@]}"; do
    b=$(basename "$f")
    if skip_noise "$b"; then
        continue
    fi
    filtered+=("$f")
done
all=("${filtered[@]}")

if [ "${#all[@]}" -eq 0 ]; then
    echo "No files under ${DIR} (after excluding electron-builder debug YAML)" >&2
    exit 1
fi

declare -A seen
for f in "${all[@]}"; do
    b=$(basename "$f")
    seen[$b]=$((${seen[$b]:-0} + 1))
done

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

for f in "${all[@]}"; do
    b=$(basename "$f")
    if [ "${seen[$b]}" -gt 1 ]; then
        rel="${f#"$DIR"/}"
        name="${rel//\//__}"
    else
        name="$b"
    fi
    cp -- "$f" "$STAGE/$name"
done

mapfile -t files < <(find "$STAGE" -type f)
gh release upload "$TAG" "${files[@]}" --clobber
