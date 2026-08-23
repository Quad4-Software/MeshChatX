#!/bin/sh
# Validate the commit message with commitlint.
# SPDX-License-Identifier: 0BSD
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

NPM="${NPM:-pnpm}"
exec "$NPM" exec commitlint --edit "$1"
