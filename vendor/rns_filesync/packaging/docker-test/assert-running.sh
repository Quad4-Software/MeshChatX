#!/bin/sh
# Assert daemon is alive as rns-filesync for a few seconds.
set -eu
pid="$1"
user="${2:-rns-filesync}"
i=0
while [ "$i" -lt 8 ]; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "FAIL: process $pid died"
    exit 1
  fi
  owner="$(ps -o user= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  if [ -n "$owner" ] && [ "$owner" != "$user" ]; then
    echo "FAIL: pid $pid owner is '$owner' expected '$user'"
    exit 1
  fi
  i=$((i + 1))
  sleep 1
done
echo "OK: pid $pid running as $user for ${i}s"
kill "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
