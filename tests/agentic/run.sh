#!/usr/bin/env bash
# Agentic test suite orchestrator.
#
# Deterministic legs always run. LLM legs run only when a provider is
# configured via env (see README). Usage:
#   bash tests/agentic/run.sh              # deterministic legs
#   bash tests/agentic/run.sh --llm        # + LLM-assisted legs
#   bash tests/agentic/run.sh --electron   # + electron update flow (needs built app + xvfb)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_URL="${AGENTIC_BASE_URL:-http://127.0.0.1:5173}"
OUT=tests/agentic/out
mkdir -p "$OUT"

WANT_LLM=0 WANT_ELECTRON=0 WANT_PAIR=0
for a in "$@"; do
    case "$a" in
        --llm) WANT_LLM=1 ;;
        --electron) WANT_ELECTRON=1 ;;
        --pair) WANT_PAIR=1 ;;
        *) echo "unknown flag $a"; exit 2 ;;
    esac
done

# Bring the e2e stack up if nothing is listening.
if ! curl -sf "$BASE_URL/" -o /dev/null; then
    echo "[run] starting e2e stack"
    nohup bash scripts/e2e/start-e2e-stack.sh > "$OUT/stack.log" 2>&1 &
    for _ in $(seq 1 120); do
        curl -sf "$BASE_URL/" -o /dev/null && break
        sleep 2
    done
fi

rc=0
run() {
    echo "=== $1"
    if ! "$@"; then rc=1; fi
}

run node tests/agentic/route-drift.cjs
run node tests/agentic/heap-profiler.cjs --json "$OUT/heap.json"
run node tests/agentic/i18n-sweep.cjs --shots "$OUT/i18n"
run node tests/agentic/adversarial.cjs

if [[ "$WANT_LLM" == "1" ]]; then
    run node tests/agentic/i18n-sweep.cjs --judge --shots "$OUT/i18n-judge"
    run node tests/agentic/adversarial.cjs --llm
fi

if [[ "$WANT_ELECTRON" == "1" ]]; then
    run node tests/agentic/electron-update-flow.cjs
fi

if [[ "$WANT_PAIR" == "1" ]]; then
    run bash tests/agentic/pair-up.sh
    run node tests/agentic/pair-messaging.cjs
    run node tests/agentic/pair-features.cjs
fi

echo "[run] done (rc=$rc); reports in $OUT"
exit "$rc"
