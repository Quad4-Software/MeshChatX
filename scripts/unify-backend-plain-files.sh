#!/usr/bin/env bash
# Make the two per-arch cx_Freeze backend trees compatible with
# @electron/universal's merge requirements:
#
#   1. Every file must exist in BOTH trees (no unique-to-one-arch files).
#   2. Every non-Mach-O file must be byte-identical across trees.
#
# Python bytecode (.pyc inside library.zip) is architecture-independent;
# only timestamps and zip metadata cause SHA differences.

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
dropped=0
normalized=0

copy_missing() {
    local src_dir="$1" dst_dir="$2" label="$3"
    while IFS= read -r -d '' rel; do
        rel="${rel#./}"
        if [[ ! -f "$dst_dir/$rel" ]]; then
            local src_file="$src_dir/$rel"
            local ft
            ft=$(file --brief --no-pad "$src_file" 2>/dev/null || true)
            if [[ "$ft" == Mach-O* ]]; then
                echo "unify-backend: dropping arch-only Mach-O for consistency: $rel" >&2
                echo "  ($label); source reports: $ft" >&2
                echo "  Hint: ensure libyaml is available for x86_64 (arch -x86_64 brew install libyaml)" >&2
                echo "  so PyYAML's C extension compiles for darwin-x64 and both trees match." >&2
                rm -f "$src_file"
                dropped=$((dropped + 1))
                continue
            fi
            mkdir -p "$dst_dir/$(dirname "$rel")"
            cp "$src_file" "$dst_dir/$rel"
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
    if [[ "$filetype" != Mach-O* ]]; then
        cp "$arm64_file" "$x64_file"
        echo "  unified: $rel"
        unified=$((unified + 1))
        continue
    fi

    x64_filetype=$(file --brief --no-pad "$x64_file" 2>/dev/null || true)
    if [[ "$x64_filetype" == Mach-O* ]] &&
       [[ "$x64_filetype" == *arm64* ]] &&
       [[ "$x64_filetype" != *universal* ]] &&
       [[ "$x64_filetype" != *x86_64* ]]; then
        cp "$arm64_file" "$x64_file"
        echo "unify-backend: normalized same-arch Mach-O (arm64 in both trees): $rel" >&2
        echo "  x64 copy replaced with arm64 tree's bytes; @electron/universal" >&2
        echo "  will use x64ArchFiles to skip lipo.  For a true universal2 binary," >&2
        echo "  ensure the x64 Python env compiles with CC=\"clang -arch x86_64\"." >&2
        normalized=$((normalized + 1))
    fi
done < <(cd "$ARM64_DIR" && find . -type f -print0)

total=$((unified + synced + normalized))
if [[ $dropped -gt 0 ]]; then
    echo "unify-backend: WARNING: dropped $dropped arch-only Mach-O binary/binaries for consistency (pure Python fallback active)"
fi
if [[ $normalized -gt 0 ]]; then
    echo "unify-backend: WARNING: normalized $normalized same-arch Mach-O file(s) (both trees had arm64; x64ArchFiles will skip lipo)"
fi
if [[ $total -gt 0 ]]; then
    echo "unify-backend: synced $synced missing file(s), unified $unified differing file(s), normalized $normalized same-arch file(s)"
else
    echo "unify-backend: all files already identical and present in both trees"
fi
