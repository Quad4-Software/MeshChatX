#!/usr/bin/env bash
# Emit base64-encoded sha256sum lines for *.apk, *.flatpak, and *.flatpakref under
# given roots (SLSA generic generator input). Writes hashes= and has_subjects= to
# GITHUB_OUTPUT when set.
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <root> [root...]" >&2
    exit 1
fi

roots=()
for d in "$@"; do
    [ -d "$d" ] && roots+=("$d")
done

write_empty() {
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        {
            echo "hashes="
            echo "has_subjects=false"
        } >>"$GITHUB_OUTPUT"
    else
        printf '%s\n' ""
    fi
}

if [ "${#roots[@]}" -eq 0 ]; then
    echo "No existing directories in: $* (no APK/Flatpak subjects)" >&2
    write_empty
    exit 0
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

find "${roots[@]}" -type f \( \
    -name '*.apk' -o -name '*.flatpak' -o -name '*.flatpakref' \
    \) ! -path '*/.*' -print0 \
    | LC_ALL=C sort -z \
    | xargs -0r sha256sum >"$tmp"

if [ ! -s "$tmp" ]; then
    echo "No .apk / .flatpak / .flatpakref under: ${roots[*]}" >&2
    write_empty
    exit 0
fi

b64="$(base64 -w0 <"$tmp")"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        echo "hashes=${b64}"
        echo "has_subjects=true"
    } >>"$GITHUB_OUTPUT"
else
    printf '%s\n' "$b64"
fi
