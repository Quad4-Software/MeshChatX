#!/bin/sh
# Filesystem vulnerability scan for Node (lockfiles, manifests). Replaces pnpm audit
# while the npm registry legacy audit endpoints are unavailable to pnpm (HTTP 410).
set -eu

# MeshChatX runtime Python deps come from uv.lock (and pip-audit). Vendored trees may
# ship upstream poetry.lock files for standalone development only. Skip them here.
# openvex.json suppresses findings a statement marks not_affected or fixed.
exec trivy fs --exit-code 1 --severity HIGH,CRITICAL \
    --vex openvex.json \
    --skip-dirs .pnpm-store,.venv,temp-tests \
    --skip-files vendor/lxmfy/poetry.lock,vendor/lxmfy/docs/poetry.lock \
    .
