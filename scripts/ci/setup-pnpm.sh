#!/bin/sh
# Activate pnpm via corepack.
# Usage: setup-pnpm.sh [version]
set -eu

export PATH="/usr/local/bin:$PATH"

PNPM_VERSION="${1:-10.32.1}"

corepack enable
corepack prepare "pnpm@${PNPM_VERSION}" --activate

pnpm --version
