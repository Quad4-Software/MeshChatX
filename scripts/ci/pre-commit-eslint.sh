#!/bin/sh
# ESLint --fix on staged JS/TS/Svelte files. Requires pnpm install.
# SPDX-License-Identifier: 0BSD
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

files=""
for path in "$@"; do
	case "$path" in
	*.js | *.mjs | *.cjs | *.ts | *.svelte) files="$files $path" ;;
	esac
done

if [ -z "${files# }" ]; then
	exit 0
fi

NPM="${NPM:-pnpm}"
# shellcheck disable=SC2086
exec "$NPM" exec eslint --fix $files
