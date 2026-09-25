#!/usr/bin/env bash
# DAST baseline: boot the backend headless and run OWASP ZAP baseline scan.
# Warn-only by design: findings land in the JSON report artifact and the
# step summary. Graduate confirmed issues into tests, not silent gates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PORT="${DAST_PORT:-18099}"
ZAP_IMAGE="${ZAP_IMAGE:-ghcr.io/zaproxy/zaproxy:stable}"
REPORT_DIR="${DAST_REPORT_DIR:-$ROOT/reports/dast}"
mkdir -p "$REPORT_DIR"

export MESHCHAT_NO_HTTPS=1
export MESHCHAT_LANDLOCK=0
export MESHCHAT_TRUSTED_PROXIES="${MESHCHAT_TRUSTED_PROXIES:-127.0.0.1/32}"

TMPDIR="$(mktemp -d -t meshchat-dast-XXXXXX)"
export MESHCHAT_LOG_DIR="$TMPDIR/logs"
mkdir -p "$MESHCHAT_LOG_DIR"

cleanup() {
    if [[ -n "${BACK_PID:-}" ]] && kill -0 "$BACK_PID" 2>/dev/null; then
        kill "$BACK_PID" 2>/dev/null || true
        wait "$BACK_PID" 2>/dev/null || true
    fi
    rm -rf "$TMPDIR"
}
trap cleanup EXIT INT TERM

echo "DAST: starting backend on 127.0.0.1:${PORT}"
uv run python -m meshchatx.meshchat \
    --headless \
    --no-https \
    --host 127.0.0.1 \
    --port "${PORT}" \
    --storage-dir "$TMPDIR/storage" \
    --reticulum-config-dir "$TMPDIR/rns" \
    &
BACK_PID=$!

ready=0
for i in $(seq 1 240); do
    if ! kill -0 "$BACK_PID" 2>/dev/null; then
        echo "DAST: backend exited before ready" >&2
        exit 1
    fi
    if body="$(curl -sf "http://127.0.0.1:${PORT}/api/v1/status" 2>/dev/null)"; then
        if printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" or d.get("network_ready") else 1)'; then
            ready=1
            echo "DAST: backend ready after ${i}s"
            break
        fi
    fi
    sleep 1
done
if [[ "$ready" != "1" ]]; then
    echo "DAST: backend never became ready" >&2
    exit 1
fi

docker run --rm \
    --network host \
    -v "$REPORT_DIR:/zap/wrk/:rw" \
    -t "$ZAP_IMAGE" \
    zap-baseline.py \
    -t "http://127.0.0.1:${PORT}" \
    -J dast-report.json \
    -r dast-report.html \
    -w dast-report.md \
    -a -j || true

echo "DAST: reports written to ${REPORT_DIR}"
