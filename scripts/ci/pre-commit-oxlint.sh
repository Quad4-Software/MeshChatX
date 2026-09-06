#!/bin/sh
# Oxlint on staged JS/TS files (Svelte stays on ESLint). Requires pnpm install.
# SPDX-License-Identifier: 0BSD
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

files=""
for path in "$@"; do
	case "$path" in
	*.js | *.mjs | *.cjs | *.ts) files="$files $path" ;;
	esac
done

if [ -z "${files# }" ]; then
	exit 0
fi

NPM="${NPM:-pnpm}"
# shellcheck disable=SC2086
exec "$NPM" exec oxlint --config .oxlintrc.json $files
