#!/usr/bin/env bash
# Build Windows portable + NSIS installers (electron-builder). See package.json dist:windows.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

git config --global core.longpaths true 2>/dev/null || true

pnpm run dist:windows
