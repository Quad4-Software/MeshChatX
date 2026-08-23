#!/bin/sh
# Point this clone at tracked .githooks/ and install pre-commit hook environments.
# SPDX-License-Identifier: 0BSD
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg
chmod +x scripts/ci/pre-commit-tree-rsm.sh
chmod +x scripts/ci/pre-commit-eslint.sh
chmod +x scripts/ci/pre-commit-commitlint.sh

if command -v uv >/dev/null 2>&1; then
	echo "install-git-hooks.sh: installing pre-commit hook environments"
	uv run pre-commit install-hooks
else
	echo "install-git-hooks.sh: uv not found, skipping pre-commit install-hooks" >&2
	echo "install-git-hooks.sh: run task install && task hooks:install after deps are ready" >&2
fi

echo "install-git-hooks.sh: core.hooksPath=.githooks"
echo "install-git-hooks.sh: pre-commit formats staged files and resigns meshchatx.rsm when possible"
echo "install-git-hooks.sh: commit-msg runs commitlint (conventional commits)"
