#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Pre-create pnpm's store operation-lock directory. pnpm 12 fails with
# ERR_PNPM_STORE_DIR_OPEN_OPERATION_LOCK on a fresh runner (or a restored
# store cache) because it does not create <store>/pnpm-store-operation-locks
# before opening lock files inside it.
set -eu

store="$(pnpm store path 2>/dev/null || true)"
if [ -z "${store}" ]; then
    store="${XDG_DATA_HOME:-${HOME}/.local/share}/pnpm/store/v11"
fi
mkdir -p "${store}/pnpm-store-operation-locks"
echo "ensure-pnpm-store: ready ${store}"
