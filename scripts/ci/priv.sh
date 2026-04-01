# shellcheck shell=sh
# Sourced by scripts/ci/*.sh — run commands as root when sudo is missing (e.g. Docker, act).
# Usage: . "$(dirname "$0")/priv.sh"

run_priv() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo "run_priv: need root or sudo for: $*" >&2
        exit 1
    fi
}
