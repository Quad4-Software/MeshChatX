#!/usr/bin/env bash
# Start backend (+ Vite or production static) for tests/ui Playwright suites.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-18079}"
export MESHCHAT_NO_HTTPS=1
export MESHCHAT_LANDLOCK=0
export MESHCHAT_VUE_DEVTOOLS=0

if [[ "${MESHCHAT_UI_PROD:-0}" == "1" ]]; then
    export MESHCHAT_LOG_DIR="${MESHCHAT_LOG_DIR:-$(mktemp -d -t meshchat-ui-XXXXXX)/logs}"
    mkdir -p "$MESHCHAT_LOG_DIR"
    TMPDIR="$(dirname "$MESHCHAT_LOG_DIR")"

    cleanup() {
        if [[ -n "${BACK_PID:-}" ]] && kill -0 "$BACK_PID" 2>/dev/null; then
            kill "$BACK_PID" 2>/dev/null || true
            wait "$BACK_PID" 2>/dev/null || true
        fi
        rm -rf "$TMPDIR"
    }
    trap cleanup EXIT INT TERM

    if [[ "${MESHCHAT_LH_SKIP_BUILD:-0}" == "1" ]] \
        && [[ -f meshchatx/public/index.html ]] \
        && compgen -G "meshchatx/public/assets/app-*.js" > /dev/null; then
        echo "UI: reusing existing meshchatx/public assets"
    else
        if [[ "${MESHCHAT_LH_SKIP_BUILD:-0}" == "1" ]]; then
            echo "UI: public assets missing or incomplete, building frontend"
        else
            echo "UI: building frontend for production-style Lighthouse scores"
        fi
        pnpm run build-frontend
    fi

    echo "UI: starting MeshChat backend (static public/) on 127.0.0.1:${E2E_BACKEND_PORT}"
    uv run python -m meshchatx.meshchat \
        --headless \
        --no-https \
        --host 127.0.0.1 \
        --port "${E2E_BACKEND_PORT}" \
        --storage-dir "$TMPDIR/storage" \
        --reticulum-config-dir "$TMPDIR/rns" \
        &
    BACK_PID=$!

    ready=0
    for i in $(seq 1 240); do
        if ! kill -0 "$BACK_PID" 2>/dev/null; then
            echo "UI: backend exited before ready"
            exit 1
        fi
        if body="$(curl -sf "http://127.0.0.1:${E2E_BACKEND_PORT}/api/v1/status" 2>/dev/null)"; then
            if printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" else 1)'; then
                ready=1
                echo "UI: backend ready after ${i}s"
                break
            fi
        fi
        sleep 1
    done
    if [[ "$ready" -ne 1 ]]; then
        echo "UI: backend did not become ready"
        exit 1
    fi

    # Keep the script alive while Playwright drives the browser.
    wait "$BACK_PID"
else
    exec bash scripts/e2e/start-e2e-stack.sh
fi
