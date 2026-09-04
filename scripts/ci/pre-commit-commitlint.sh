#!/bin/sh
# Validate the commit message with commitlint.
# Call the local binary. Do not use pnpm exec (slow and can stall on the store lock).
# SPDX-License-Identifier: 0BSD
set -eu

MSG_FILE="${1:-}"
if [ -z "$MSG_FILE" ] || [ ! -f "$MSG_FILE" ]; then
	echo "commitlint: missing commit message file" >&2
	exit 1
fi

# Merge and similar messages are ignored by commitlint. Exit early to avoid
# spinning Node during git merge/rebase when the message is already fine.
if grep -qE '^(Merge |Revert |fixup! |squash! )' "$MSG_FILE"; then
	exit 0
fi

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

BIN="$ROOT/node_modules/.bin/commitlint"
if [ ! -x "$BIN" ]; then
	echo "commitlint: $BIN missing. Run: task install" >&2
	exit 1
fi

exec "$BIN" --edit "$MSG_FILE"
