#!/usr/bin/env bash
# Launch the paired agents: Alice drives :5173, Bob drives :18081.
# Both read pairshare/pair.json and rendezvous through marker files.
#
#   bash tests/agentic/pair-agents.sh [model]
#   OPENCODE_API_KEY=oc_sk_... bash tests/agentic/pair-agents.sh opencode/space-bunny-free
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
MODEL="${1:-${AGENTIC_PAIR_MODEL:-opencode/space-bunny-free}}"
SHARE=out/pairshare

# Clean rendezvous state from any previous run.
rm -f "$SHARE"/alice_step_*_done.txt "$SHARE"/bob_step_*_done.txt

echo "pair-agents: alice + bob on model $MODEL"
echo "pair-agents: alice log $SHARE/alice.log, bob log $SHARE/bob.log"

opencode run --model "$MODEL" --agent crawler \
    "Read prompts/pair-alice.md and follow it exactly." \
    > "$SHARE/alice.log" 2>&1 &
A_PID=$!

opencode run --model "$MODEL" --agent crawler \
    "Read prompts/pair-bob.md and follow it exactly." \
    > "$SHARE/bob.log" 2>&1 &
B_PID=$!

wait "$A_PID"; A_RC=$?
wait "$B_PID"; B_RC=$?

echo "pair-agents: alice rc=$A_RC bob rc=$B_RC"
grep -cE "FINDING|FAIL" "$SHARE/alice.log" "$SHARE/bob.log" 2>/dev/null | sed 's/^/  findings /'

# Rendezvous completeness is the health signal: every step marker present.
missing=0
for i in 1 2 3 4 5; do
    [[ -f "$SHARE/alice_step_${i}_done.txt" ]] || { echo "missing alice step $i"; missing=1; }
    [[ -f "$SHARE/bob_step_${i}_done.txt" ]] || { echo "missing bob step $i"; missing=1; }
done
exit $(( missing || (A_RC != 0 || B_RC != 0) ))
