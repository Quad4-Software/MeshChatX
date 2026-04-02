#!/usr/bin/env bash
# Build macOS universal (x64 + arm64) DMG via electron-builder. Unsigned CI build; signing is disabled.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CSC_IDENTITY_AUTO_DISCOVERY=false

pnpm run dist:mac-universal
