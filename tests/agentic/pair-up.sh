#!/usr/bin/env bash
# Bring up a second MeshChatX instance (Bob) linked to the e2e stack
# instance (Alice) over a TCPClientInterface through the chaos proxy.
#
#   Alice  http://127.0.0.1:5173 (vite) / :18079 (backend), TCPServer :43737
#   Chaos  :43837 -> 43737 (fault injection point)
#   Bob    http://127.0.0.1:18081 (backend serves built frontend)
#
# Writes tests/agentic/out/pairshare/pair.env and pair.json once both are
# up and announced. Stop Bob with tests/agentic/pair-down.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ALICE_URL="${AGENTIC_ALICE_URL:-http://127.0.0.1:5173}"
ALICE_API="${AGENTIC_ALICE_API:-http://127.0.0.1:18079}"
BOB_URL="${AGENTIC_BOB_URL:-http://127.0.0.1:18081}"
BOB_PORT="${AGENTIC_BOB_PORT:-18081}"
CHAOS_PORT="${E2E_CHAOS_PORT:-43837}"

SHARE="tests/agentic/out/pairshare"
DATA_B="${AGENTIC_PAIR_B_DATA:-tests/agentic/out/pair-b}"
RNS_B="$DATA_B/reticulum"
mkdir -p "$SHARE" "$RNS_B"

# Bob links through the chaos proxy so fault injection stays possible.
cat > "$RNS_B/config" <<EOF
[reticulum]
  enable_transport = False
  share_instance = Yes
  instance_name = agentic-pair-b
  shared_instance_port = 47528
  instance_control_port = 47529
  loglevel = 3
[interfaces]
  [[Pair Link]]
    type = TCPClientInterface
    enabled = Yes
    target_host = 127.0.0.1
    target_port = ${CHAOS_PORT}
EOF

free_port() {
    if ss -tln "sport = :$1" | grep -q LISTEN; then
        echo "pair-up: port $1 already bound" >&2
        exit 1
    fi
}
if curl -sf "$BOB_URL/api/v1/app/info" -o /dev/null; then
    echo "pair-up: Bob already running on :$BOB_PORT, reusing"
else
    free_port "$BOB_PORT"

    export MESHCHAT_NO_HTTPS=1 MESHCHAT_HEADLESS=1 MESHCHAT_LANDLOCK=0
    export MESHCHAT_LOG_DIR="$DATA_B/logs"
    mkdir -p "$MESHCHAT_LOG_DIR"

    echo "pair-up: starting Bob on :$BOB_PORT (data $DATA_B, rns via chaos :$CHAOS_PORT)"
    nohup uv run python -m meshchatx.meshchat \
        --headless --no-https \
        --host 127.0.0.1 --port "$BOB_PORT" \
        --storage-dir "$DATA_B/storage" --reticulum-config-dir "$RNS_B" \
        > "$SHARE/bob.log" 2>&1 &
    echo $! > "$SHARE/bob.pid"

    for i in $(seq 1 120); do
        if curl -sf "$BOB_URL/api/v1/app/info" -o /dev/null; then
            echo "pair-up: Bob up after ${i}s"
            break
        fi
        if [[ "$i" == "120" ]]; then
            echo "pair-up: Bob failed to start; see $SHARE/bob.log" >&2
            tail -30 "$SHARE/bob.log" >&2 || true
            exit 1
        fi
        sleep 1
    done
fi

# CSRF tokens are bound to the session cookie. Keep a jar per instance.
post() { # post <base-url> <path> <json>
    local base="$1" jar; jar="$(mktemp -t mcx-cookies-XXXXXX)"
    local token; token="$(curl -sf -c "$jar" "$base/api/v1/auth/csrf" \
        | python3 -c "import json,sys;print(json.load(sys.stdin)['csrf_token'])")"
    curl -sf -X POST "$base$2" -b "$jar" -H "content-type: application/json" \
        -H "X-CSRF-Token: $token" -d "$3" -o /dev/null
    local rc=$?; rm -f "$jar"; return $rc
}
patch_cfg() { # patch_cfg <base-url> <json>
    local base="$1" jar; jar="$(mktemp -t mcx-cookies-XXXXXX)"
    local token; token="$(curl -sf -c "$jar" "$base/api/v1/auth/csrf" \
        | python3 -c "import json,sys;print(json.load(sys.stdin)['csrf_token'])")"
    curl -sf -X PATCH "$base/api/v1/config" -b "$jar" -H "content-type: application/json" \
        -H "X-CSRF-Token: $token" -d "$2" -o /dev/null
    local rc=$?; rm -f "$jar"; return $rc
}

# Dismiss first-run UI on both sides and give them stable names.
post "$BOB_URL" /api/v1/app/tutorial/seen '{}'
post "$BOB_URL" /api/v1/app/changelog/seen '{"version":"999.999.999"}'
post "$ALICE_API" /api/v1/app/tutorial/seen '{}'
post "$ALICE_API" /api/v1/app/changelog/seen '{"version":"999.999.999"}'
patch_cfg "$ALICE_API" '{"display_name":"Alice"}'
patch_cfg "$BOB_URL" '{"display_name":"Bob"}'

addr() {
    curl -sf "$1/api/v1/config" | python3 -c "import json,sys;print(json.load(sys.stdin)['config']['lxmf_address_hash'])"
}
A_ADDR="$(addr "$ALICE_API")"
B_ADDR="$(addr "$BOB_URL")"

# Trigger announces on both sides, then wait for mutual propagation:
# Alice needs Bob's hash to send to him, Bob needs Alice's to reply.
post "$BOB_URL" /api/v1/announce '{}' || true
post "$ALICE_API" /api/v1/announce '{}' || true

echo "pair-up: waiting for mutual announce propagation"
for i in $(seq 1 120); do
    a_sees=0 b_sees=0
    curl -sf "$ALICE_API/api/v1/announces?limit=200" | grep -q "$B_ADDR" && a_sees=1
    curl -sf "$BOB_URL/api/v1/announces?limit=200" | grep -q "$A_ADDR" && b_sees=1
    if [[ "$a_sees" == "1" && "$b_sees" == "1" ]]; then
        echo "pair-up: mutual announces after ${i}s"
        break
    fi
    # Re-announce periodically: first announce may race the link handshake.
    if (( i % 15 == 0 )); then
        post "$BOB_URL" /api/v1/announce '{}' || true
        post "$ALICE_API" /api/v1/announce '{}' || true
    fi
    if [[ "$i" == "120" ]]; then
        echo "pair-up: announce propagation timed out (a_sees=$a_sees b_sees=$b_sees)" >&2
        echo "pair-up: continuing anyway; sends may fail until announce lands" >&2
    fi
    sleep 2
done

cat > "$SHARE/pair.env" <<EOF
AGENTIC_ALICE_URL=$ALICE_URL
AGENTIC_ALICE_API=$ALICE_API
AGENTIC_BOB_URL=$BOB_URL
AGENTIC_ALICE_ADDR=$A_ADDR
AGENTIC_BOB_ADDR=$B_ADDR
AGENTIC_PAIRSHARE=$PWD/$SHARE
EOF
python3 - "$SHARE/pair.json" "$ALICE_URL" "$ALICE_API" "$BOB_URL" "$A_ADDR" "$B_ADDR" <<'PY'
import json, sys
path, a_url, a_api, b_url, a, b = sys.argv[1:7]
json.dump({
    "alice": {"url": a_url, "api": a_api, "lxmf_address": a},
    "bob": {"url": b_url, "lxmf_address": b},
}, open(path, "w"), indent=2)
PY

echo "pair-up: Alice=$A_ADDR Bob=$B_ADDR"
echo "pair-up: share env at $SHARE/pair.env"
