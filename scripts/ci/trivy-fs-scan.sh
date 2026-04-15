#!/bin/sh
# Filesystem vulnerability scan for Node (lockfiles, manifests). Replaces pnpm audit
# while the npm registry legacy audit endpoints are unavailable to pnpm (HTTP 410).
set -eu

exec trivy fs --exit-code 1 --severity HIGH,CRITICAL --skip-dirs .pnpm-store .
