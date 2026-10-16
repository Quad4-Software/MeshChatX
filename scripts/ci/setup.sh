#!/usr/bin/env bash
# Portable CI setup (no GitHub Actions).
set -euo pipefail

. "$(dirname "$0")/env.sh"

if ! ci_truthy "${CI_SKIP_BOOTSTRAP:-}"; then
	if ci_truthy "${CI_BOOTSTRAP_INSTALL:-}"; then
		bash "$ROOT/scripts/ci/bootstrap-toolchain.sh" install
	else
		bash "$ROOT/scripts/ci/bootstrap-toolchain.sh" verify || bash "$ROOT/scripts/ci/bootstrap-toolchain.sh" install
	fi
fi

require_cmd uv
require_cmd pnpm
require_task

task install

echo "ci setup: OK"
