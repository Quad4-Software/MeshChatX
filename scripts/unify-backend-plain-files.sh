#!/usr/bin/env bash
# Make the two per-arch cx_Freeze backend trees compatible with
# @electron/universal's merge requirements:
#
#   1. Every file must exist in BOTH trees (no unique-to-one-arch files).
#   2. Every non-Mach-O file must be byte-identical across trees.
#
# Python bytecode (.pyc inside library.zip) is architecture-independent;
# only timestamps and zip metadata cause SHA differences.
#
# Native extensions (.so/.dylib) that exist in only one tree are copied
# to the other so the file sets match. The copy won't load on the wrong
# arch at runtime, but the owning package (e.g. PyYAML) falls back to
# its pure-Python implementation, so this is safe.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ARM64_DIR="$ROOT/build/exe/darwin-arm64"
X64_DIR="$ROOT/build/exe/darwin-x64"

if [[ ! -d "$ARM64_DIR" || ! -d "$X64_DIR" ]]; then
    echo "unify-backend: one or both backend dirs missing, skipping"
    exit 0
fi

unified=0
synced=0

copy_missing() {
    local src_dir="$1" dst_dir="$2" label="$3"
    while IFS= read -r -d '' rel; do
        rel="${rel#./}"
        if [[ ! -f "$dst_dir/$rel" ]]; then
            mkdir -p "$dst_dir/$(dirname "$rel")"
            cp "$src_dir/$rel" "$dst_dir/$rel"
            echo "  synced ($label): $rel"
            synced=$((synced + 1))
        fi
    done < <(cd "$src_dir" && find . -type f -print0)
}

copy_missing "$ARM64_DIR" "$X64_DIR" "arm64 -> x64"
copy_missing "$X64_DIR" "$ARM64_DIR" "x64 -> arm64"

while IFS= read -r -d '' rel; do
    rel="${rel#./}"
    arm64_file="$ARM64_DIR/$rel"
    x64_file="$X64_DIR/$rel"

    [[ -f "$x64_file" ]] || continue

    if cmp -s "$arm64_file" "$x64_file"; then
        continue
    fi

    filetype=$(file --brief --no-pad "$arm64_file" 2>/dev/null || true)
    if [[ "$filetype" == Mach-O* ]]; then
        continue
    fi

    cp "$arm64_file" "$x64_file"
    echo "  unified: $rel"
    unified=$((unified + 1))
done < <(cd "$ARM64_DIR" && find . -type f -print0)

total=$((unified + synced))
if [[ $total -gt 0 ]]; then
    echo "unify-backend: synced $synced missing file(s), unified $unified differing file(s)"
else
    echo "unify-backend: all files already identical and present in both trees"
fi
