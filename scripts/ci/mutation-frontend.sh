#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "Running MeshMut mutation testing (frontend)"

node scripts/mutation/run.mjs "$@"
