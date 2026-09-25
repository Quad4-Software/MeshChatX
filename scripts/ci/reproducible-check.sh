#!/usr/bin/env bash
# Reproducibility probe: build the wheel twice and compare SHA256.
# SOURCE_DATE_EPOCH pins archive timestamps; remaining nondeterminism
# (ordering, embedded paths) is exactly what this check exists to catch.
set -euo pipefail

EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
A="$(mktemp -d)/a"
B="$(mktemp -d)/b"
mkdir -p "$A" "$B"
trap 'rm -rf "$(dirname "$A")"' EXIT

for out in "$A" "$B"; do
    SOURCE_DATE_EPOCH="$EPOCH" uv build --wheel --out-dir "$out" >/dev/null
done

fail=0
for f in "$A"/*.whl; do
    name="$(basename "$f")"
    ha="$(sha256sum "$f" | cut -d' ' -f1)"
    hb="$(sha256sum "$B/$name" | cut -d' ' -f1)"
    if [ "$ha" = "$hb" ]; then
        echo "REPRODUCIBLE $name $ha"
    else
        echo "DIFFERS $name a=$ha b=$hb"
        fail=1
    fi
done
exit "$fail"
