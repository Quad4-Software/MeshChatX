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

mapfile -d '' -t all < <(
    find "$DIR" -type f \
        ! -path '*/win-unpacked/*' \
        ! -path '*/linux-unpacked/*' \
        ! -path '*/mac-universal/*' \
        ! -path '*/mac-arm64/*' \
        ! -path '*/mac-x64/*' \
        ! -path '*/mac/*.app/*' \
        -print0
)

skip_noise() {
    local base="$1"
    case "$base" in
        builder-debug.yml | builder-debug.yml.cosign.bundle) return 0 ;;
        *__builder-debug.yml | *__builder-debug.yml.cosign.bundle) return 0 ;;
        library.zip | library.zip.cosign.bundle) return 0 ;;
        *__library.zip | *__library.zip.cosign.bundle) return 0 ;;
        *.so.yml | *.so.yml.cosign.bundle) return 0 ;;
        *__*.so.yml | *__*.so.yml.cosign.bundle) return 0 ;;
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
notes_file=$(mktemp)
trap 'rm -rf "$STAGE" "$notes_file"' EXIT

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

{
    echo "Automated draft release. Review assets and provenance before publishing."
    echo
    echo "## SHA256 Checksums"
    echo
    echo "| Asset | SHA256 |"
    echo "|-------|--------|"
    for f in "${files[@]}"; do
        b=$(basename "$f")
        hash=$(sha256sum "$f" | awk '{print $1}')
        printf '| %s | `%s` |\n' "$b" "$hash"
    done
    echo
    echo "## Verification"
    echo
    echo "- **Cosign bundles** (\`.cosign.bundle\`) are attached for keyless sigstore verification."
    echo "- **SLSA provenance** (\`.intoto.jsonl\`) is available for supply-chain attestation."
    echo "- Or verify manually using the SHA256 table above."
} > "$notes_file"

if ! gh release view "$TAG" >/dev/null 2>&1; then
    gh release create "$TAG" --draft --title "$TAG" --notes-file "$notes_file"
else
    gh release edit "$TAG" --notes-file "$notes_file"
fi

for f in "${files[@]}"; do
    gh release upload "$TAG" "$f" --clobber
done
