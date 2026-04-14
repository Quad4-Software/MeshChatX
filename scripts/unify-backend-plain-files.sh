#!/usr/bin/env bash
# Ensure non-binary files in the two per-arch cx_Freeze outputs are
# byte-identical so @electron/universal's SHA check passes.
#
# Python bytecode (.pyc inside library.zip) is architecture-independent;
# only timestamps and zip metadata differ between the arm64 and x64
# builds.  Native extensions (.dylib/.so) are Mach-O binaries and
# handled separately by lipo, so they are excluded here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ARM64_DIR="$ROOT/build/exe/darwin-arm64"
X64_DIR="$ROOT/build/exe/darwin-x64"

if [[ ! -d "$ARM64_DIR" || ! -d "$X64_DIR" ]]; then
    echo "unify-backend-plain-files: one or both backend dirs missing, skipping"
    exit 0
fi

unified=0

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

if [[ $unified -gt 0 ]]; then
    echo "unify-backend-plain-files: copied $unified file(s) from arm64 → x64"
else
    echo "unify-backend-plain-files: all non-binary files already identical"
fi
