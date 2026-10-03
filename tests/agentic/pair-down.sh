#!/usr/bin/env bash
# Stop the paired second instance started by pair-up.sh.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SHARE="$ROOT/tests/agentic/out/pairshare"

if [[ -f "$SHARE/bob.pid" ]]; then
    pid="$(cat "$SHARE/bob.pid")"
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        echo "pair-down: stopped Bob (pid $pid)"
    fi
    rm -f "$SHARE/bob.pid"
else
    echo "pair-down: no pid file; nothing to stop"
fi
