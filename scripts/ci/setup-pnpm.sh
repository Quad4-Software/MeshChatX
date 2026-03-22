#!/bin/sh
# Activate pnpm via corepack.
# Usage: setup-pnpm.sh [version]
set -eu

PNPM_VERSION="${1:-10.30.0}"

corepack enable
corepack prepare "pnpm@${PNPM_VERSION}" --activate

pnpm --version
