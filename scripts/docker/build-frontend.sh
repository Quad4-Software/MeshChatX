#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Build MeshChatX frontend assets inside a Node image stage.
# Expects WORKDIR with package manifests, patches, scripts, docs, and frontend tree.
set -eu

mkdir -p /tmp/go-cache /tmp/go-tmp
export GOCACHE="${GOCACHE:-/tmp/go-cache}"
export GOTMPDIR="${GOTMPDIR:-/tmp/go-tmp}"

PNPM_VERSION="${MESHCHATX_PNPM_VERSION:-11.1.2}"

corepack enable
corepack prepare "pnpm@${PNPM_VERSION}" --activate
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
node scripts/ensure-micron-parser-package.js
MESHCHATX_REQUIRE_VISUALISER_WASM=1 pnpm run build-frontend

test -s meshchatx/src/frontend/public/vendor/visualiser-wasm/visualiser.wasm
test -s meshchatx/src/frontend/public/vendor/visualiser-wasm/wasm_exec.js
test -s meshchatx/src/frontend/public/vendor/micron-parser-go/micron-parser-go.wasm
test -s meshchatx/src/frontend/public/vendor/micron-parser-go/wasm_exec.js

pnpm run build-docs
