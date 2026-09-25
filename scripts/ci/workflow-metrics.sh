#!/usr/bin/env bash
# Summarize workflow run durations + failure rate over the last N days.
# Writes a table to $GITHUB_STEP_SUMMARY (falls back to stdout).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "${ROOT}/scripts/ci/workflow-metrics.py"
