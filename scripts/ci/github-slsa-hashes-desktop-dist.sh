#!/usr/bin/env bash
# Emit base64-encoded sha256sum lines for Electron outputs under downloaded artifact roots.
# Subject paths are the relative paths passed to sha256sum (stable for slsa-verifier).
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <root> [root...]" >&2
    exit 1
fi

roots=()
for d in "$@"; do
    [ -d "$d" ] && roots+=("$d")
done
if [ "${#roots[@]}" -eq 0 ]; then
    echo "No existing directories in: $*" >&2
    exit 1
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

find "${roots[@]}" -type f \( \
    -name '*.exe' -o -name '*.dmg' -o -name '*.blockmap' -o -name '*.yml' -o -name '*.yaml' \
    \) ! -path '*/.*' -print0 \
    | LC_ALL=C sort -z \
    | xargs -0r sha256sum >"$tmp"

if [ ! -s "$tmp" ]; then
    echo "No matching dist files under: ${roots[*]}" >&2
    exit 1
fi

b64="$(base64 -w0 <"$tmp")"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "hashes=${b64}" >>"$GITHUB_OUTPUT"
else
    printf '%s\n' "$b64"
fi
