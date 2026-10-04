#!/usr/bin/env bash
# Run CI jobs outside GitHub Actions (local shell, Forgejo, Gitea, Podman).
#
# Usage:
#   bash scripts/ci/run.sh <job>
#
# Jobs:
#   pr         lint + backend + frontend + lang tests (verify matrix subset)
#   lint       task lint
#   test       task test
#   check      task check (format, lint, test)
#   list       Print job names
#
# Env:
#   CI_SKIP_SETUP=1        Skip setup.sh
#   CI_SKIP_TREE_VERIFY=1  Skip meshchatx.rsm verify
#   RNS_INVENTORY_OUT      End-of-job workspace clean check
set -euo pipefail

. "$(dirname "$0")/env.sh"

run_setup() {
	if ci_truthy "${CI_SKIP_SETUP:-}"; then
		return 0
	fi
	bash "$ROOT/scripts/ci/setup.sh"
}

job_pr() {
	run_setup
	require_task
	task lint
	task test:backend
	task test:frontend
	task test:lang
	verify_workspace_clean
}

job_lint() {
	run_setup
	require_task
	task lint
	verify_workspace_clean
}

job_test() {
	run_setup
	require_task
	task test
	verify_workspace_clean
}

job_check() {
	run_setup
	require_task
	task check
	verify_workspace_clean
}

usage() {
	sed -n '6,16p' "$0" | sed 's/^# \?//'
}

job="${1:-pr}"
case "$job" in
list)
	echo "pr lint test check"
	;;
pr) job_pr ;;
lint) job_lint ;;
test) job_test ;;
check) job_check ;;
-h | --help | help)
	usage
	;;
*)
	echo "ci: unknown job: $job" >&2
	usage >&2
	exit 2
	;;
esac
