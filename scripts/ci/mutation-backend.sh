#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

TARGET="${MUTMUT_TARGET:-meshchatx.src.backend.meshchat_utils*}"
THRESHOLD="${MUTMUT_MIN_SCORE:-}"
STATS_FILE="${MUTMUT_STATS_FILE:-mutmut-cicd-stats.json}"

echo "Running mutmut on: ${TARGET}"

uv run mutmut run "${TARGET}"
uv run mutmut export-cicd-stats > "${STATS_FILE}"

if [[ -n "${THRESHOLD}" ]]; then
    uv run python scripts/ci/mutation-score-check.py \
        --mutmut-stats "${STATS_FILE}" \
        --min-score "${THRESHOLD}"
fi
