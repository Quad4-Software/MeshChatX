#!/usr/bin/env bash
set -euo pipefail

shopt -s nullglob

patterns=(
  "dist/*-win-installer.exe"
  "dist/*-win-portable.exe"
  "dist/*-linux.AppImage"
  "dist/*-linux.deb"
)

for pattern in "${patterns[@]}"; do
  for f in $pattern; do
    dir=$(dirname "$f")
    base=$(basename "$f")
    ext="${base##*.}"
    name="${base%.$ext}"
    mv "$f" "$dir/${name}-legacy.${ext}"
  done
done
