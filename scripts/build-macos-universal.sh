#!/usr/bin/env bash
# Build darwin-arm64 and darwin-x64 cx_Freeze backends, then electron-builder --mac --universal.
# On Apple Silicon, the x64 backend must be built with an x86_64 Python (e.g. Homebrew in /usr/local).
# Set PYTHON_CMD_X64 to that interpreter if Poetry's default env is arm64-only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pnpm run electron-postinstall
pnpm run version:sync
pnpm run build-frontend
cross-env ARCH=arm64 pnpm run build-backend
if [[ -n "${PYTHON_CMD_X64:-}" ]]; then
    cross-env ARCH=x64 PYTHON_CMD="$PYTHON_CMD_X64" pnpm run build-backend
else
    cross-env ARCH=x64 pnpm run build-backend
fi
exec pnpm exec electron-builder --mac --universal --publish=never
