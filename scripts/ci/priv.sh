# shellcheck shell=sh
# Sourced by scripts/ci/*.sh - run commands as root when sudo is missing (e.g. Docker, act).
# Usage: . "$(dirname "$0")/priv.sh"

# Minimal self-hosted images can lose /tmp mid-run (tmpfiles cleanup,
# unmounted tmpfs). mktemp honours TMPDIR, so point it at a user-writable
# dir when /tmp is absent; GITHUB_ENV carries it to later steps.
if [ ! -d /tmp ] || [ ! -w /tmp ]; then
    _ci_tmp="${RUNNER_TEMP:-${HOME}/.meshchatx-ci}/tmp"
    mkdir -p "${_ci_tmp}" 2>/dev/null && {
        TMPDIR="${_ci_tmp}"
        export TMPDIR
        [ -n "${GITHUB_ENV:-}" ] && echo "TMPDIR=${TMPDIR}" >> "${GITHUB_ENV}"
    }
fi
unset _ci_tmp

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

# Install a single binary onto PATH: /usr/local/bin when writable or
# sudo-able, otherwise ${HOME}/.local/bin exported via GITHUB_PATH.
# Usage: install_tool <src-file> <binary-name>
install_tool() {
    _src="$1"
    _name="$2"
    if [ "$(id -u)" -eq 0 ] || [ -w /usr/local/bin ]; then
        install -m 0755 "${_src}" "/usr/local/bin/${_name}"
        return 0
    fi
    if sudo -n true 2>/dev/null; then
        sudo install -m 0755 "${_src}" "/usr/local/bin/${_name}"
        return 0
    fi
    _dest="${HOME}/.local/bin"
    mkdir -p "${_dest}"
    install -m 0755 "${_src}" "${_dest}/${_name}"
    if [ -n "${GITHUB_PATH:-}" ]; then
        echo "${_dest}" >> "${GITHUB_PATH}"
    fi
    PATH="${_dest}:${PATH}"
    export PATH
}
