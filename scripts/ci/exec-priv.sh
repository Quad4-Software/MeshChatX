#!/bin/sh
# Run a command with root privileges: use sudo only when not root (Docker/act often have no sudo).
# Usage: sh scripts/ci/exec-priv.sh apt-get update
set -eu

. "$(dirname "$0")/priv.sh"
run_priv "$@"
