#!/bin/sh
# Ensure the wails3 CLI is on PATH for desktop packaging tasks.
# Source this file (. scripts/ci/setup-wails3.sh) so the PATH export
# applies to the calling shell; safe to execute directly as well.
# Idempotent: does nothing when wails3 is already installed.
set -eu

WAILS3_VERSION="${WAILS3_VERSION:-v3.1.0}"

if ! command -v wails3 >/dev/null 2>&1; then
    if ! command -v go >/dev/null 2>&1; then
        echo "setup-wails3: go toolchain not on PATH" >&2
        exit 1
    fi

    go install "github.com/wailsapp/wails/v3/cmd/wails3@${WAILS3_VERSION}"

    _gobin="$(go env GOBIN 2>/dev/null || true)"
    if [ -z "${_gobin}" ]; then
        _gobin="$(go env GOPATH)/bin"
    fi
    _gobin_native="${_gobin}"

    # Git Bash cannot use Windows-style paths in PATH; convert C:\a\b -> /c/a/b
    # for this shell's PATH while GITHUB_PATH keeps the native form (the runner
    # hands it to later steps, and MSYS translates PATH entries itself).
    case "${_gobin}" in
        [A-Za-z]:\\*)
            _drv="$(printf '%s' "${_gobin}" | cut -c1 | tr '[:upper:]' '[:lower:]')"
            _rest="$(printf '%s' "${_gobin}" | cut -c3- | tr '\\' '/')"
            _gobin="/${_drv}${_rest}"
            ;;
    esac

    case ":${PATH}:" in
        *":${_gobin}:"*) ;;
        *)
            PATH="${_gobin}:${PATH}"
            export PATH
            ;;
    esac

    if [ -n "${GITHUB_PATH:-}" ] && ! grep -qxF "${_gobin_native}" "${GITHUB_PATH}" 2>/dev/null; then
        echo "${_gobin_native}" >> "${GITHUB_PATH}"
    fi

    if ! command -v wails3 >/dev/null 2>&1; then
        echo "setup-wails3: wails3 still not on PATH after install (looked in ${_gobin})" >&2
        exit 1
    fi
fi
