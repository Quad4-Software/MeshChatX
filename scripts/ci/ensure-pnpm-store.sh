#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Pre-create pnpm's content-addressable store root. pnpm 12 fails to open
# its store operation lock (ERR_PNPM_STORE_DIR_OPEN_OPERATION_LOCK) when
# the store directory does not exist yet on a fresh self-hosted runner.
set -eu

store="$(pnpm store path 2>/dev/null || true)"
if [ -n "${store}" ]; then
    mkdir -p "${store}"
fi
