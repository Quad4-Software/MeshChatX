#!/usr/bin/env bash
# Smoke tests for verify-package-contents.sh (no full freeze required).
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/scripts/ci/verify-package-contents.sh"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/pkg-bloat-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT INT

mkdir -p "$tmp/clean/lib/meshchatx/src/backend"
echo ok >"$tmp/clean/lib/meshchatx/src/backend/x.py"

mkdir -p "$tmp/dirty/lib/meshchatx/src/frontend/components"
mkdir -p "$tmp/dirty/lib/numpy/tests"
mkdir -p "$tmp/dirty/node_modules/left-pad"
echo vue >"$tmp/dirty/lib/meshchatx/src/frontend/components/App.vue"
echo junk >"$tmp/dirty/lib/numpy/tests/test_x.py"
echo junk >"$tmp/dirty/node_modules/left-pad/index.js"

echo "expect clean dir to pass"
bash "$SCRIPT" dir "$tmp/clean"

echo "expect clean frozen tree to pass"
bash "$SCRIPT" frozen "$tmp/clean"

echo "expect dirty frozen tree to fail"
if bash "$SCRIPT" frozen "$tmp/dirty"; then
	echo "expected failure for dirty frozen tree" >&2
	exit 1
fi

echo "expect dirty dir (node_modules) to fail"
if bash "$SCRIPT" dir "$tmp/dirty"; then
	echo "expected failure for dirty dir" >&2
	exit 1
fi

echo "verify-package-contents smoke OK"
