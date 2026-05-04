#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ARM64_DIR="$ROOT/build/exe/darwin-arm64"
X64_DIR="$ROOT/build/exe/darwin-x64"

if [[ ! -d "$ARM64_DIR" || ! -d "$X64_DIR" ]]; then
    echo "thin-backend: one or both backend dirs missing, skipping"
    exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "thin-backend: not running on macOS (uname=$(uname -s)); skipping"
    exit 0
fi

if ! command -v lipo >/dev/null 2>&1; then
    echo "thin-backend: lipo not found on PATH; skipping" >&2
    exit 0
fi

if ! command -v file >/dev/null 2>&1; then
    echo "thin-backend: file(1) not found on PATH; skipping" >&2
    exit 0
fi

STRIP_AUDIO="${MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO:-0}"

drop_audio_natives() {
    local tree="$1"
    local removed=0
    while IFS= read -r -d '' f; do
        echo "thin-backend: stripping audio native (MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO=1): ${f#"$tree"/}" >&2
        rm -f "$f"
        removed=$((removed + 1))
    done < <(find "$tree" -type f \( -name "_miniaudio*.so" -o -name "_miniaudio*.dylib" \) -print0)
    if [[ $removed -gt 0 ]]; then
        echo "thin-backend: removed $removed _miniaudio file(s) from ${tree#"$ROOT"/}"
    fi
}

if [[ "$STRIP_AUDIO" == "1" || "$STRIP_AUDIO" == "true" ]]; then
    drop_audio_natives "$ARM64_DIR"
    drop_audio_natives "$X64_DIR"
fi

thin_tree() {
    local tree="$1" want_arch="$2"
    local thinned=0 already=0 skipped=0
    while IFS= read -r -d '' f; do
        local ft
        ft=$(file --brief --no-pad "$f" 2>/dev/null || true)
        if [[ "$ft" != Mach-O* ]]; then
            continue
        fi
        if [[ "$ft" != *universal* ]]; then
            already=$((already + 1))
            continue
        fi
        local archs
        archs=$(lipo -archs "$f" 2>/dev/null || true)
        if [[ -z "$archs" ]]; then
            skipped=$((skipped + 1))
            continue
        fi
        if ! grep -qw "$want_arch" <<<"$archs"; then
            echo "thin-backend: WARNING: $f is universal but lacks $want_arch (archs=$archs); leaving as-is" >&2
            skipped=$((skipped + 1))
            continue
        fi
        local tmp
        tmp="$(mktemp -t thin-backend.XXXXXX)"
        if lipo -thin "$want_arch" "$f" -output "$tmp" 2>/dev/null; then
            cat "$tmp" >"$f"
            rm -f "$tmp"
            thinned=$((thinned + 1))
        else
            rm -f "$tmp"
            echo "thin-backend: WARNING: lipo -thin $want_arch failed on $f" >&2
            skipped=$((skipped + 1))
        fi
    done < <(find "$tree" -type f \( -name "*.so" -o -name "*.dylib" -o -name "*.bundle" \) -print0)
    echo "thin-backend: ${tree#"$ROOT"/} -> $want_arch (thinned=$thinned, already-single=$already, skipped=$skipped)"
}

thin_tree "$ARM64_DIR" arm64
thin_tree "$X64_DIR" x86_64
