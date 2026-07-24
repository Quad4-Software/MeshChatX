#!/bin/sh
# Run a command with root privileges: use sudo only when not root (Docker/act often have no sudo).
# Usage: sh scripts/ci/exec-priv.sh apt-get update
set -eu

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"
run_priv "$@"
