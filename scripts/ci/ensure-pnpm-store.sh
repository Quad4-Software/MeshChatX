#!/bin/sh
# SPDX-License-Identifier: 0BSD
# pnpm 12 keeps store operation locks under XDG_RUNTIME_DIR, falling back to
# /tmp, which may not exist on self-hosted runners. Point XDG_RUNTIME_DIR at
# a per-job dir that satisfies pnpm's ownership and permission checks, and
# make sure the pnpm store root exists. Source this script (.) rather than
# running it with sh so the exports apply to the calling step as well.
set -eu

_ci_runtime=""
for _ci_cand in "${RUNNER_TEMP:-}" "${TMPDIR:-}" "${HOME:-}"; do
    [ -n "${_ci_cand}" ] || continue
    _ci_cand="${_ci_cand}/xdg-runtime"
    if mkdir -p "${_ci_cand}" 2>/dev/null && chmod 700 "${_ci_cand}" 2>/dev/null && [ -w "${_ci_cand}" ]; then
        _ci_runtime="${_ci_cand}"
        break
    fi
done
if [ -n "${_ci_runtime}" ]; then
    XDG_RUNTIME_DIR="${_ci_runtime}"
    export XDG_RUNTIME_DIR
    [ -n "${GITHUB_ENV:-}" ] && echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR}" >> "${GITHUB_ENV}"
    echo "ensure-pnpm-store: XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR}"
fi
unset _ci_cand
unset _ci_runtime

store="$(pnpm store path 2>/dev/null || true)"
if [ -z "${store}" ]; then
    store="${XDG_DATA_HOME:-${HOME}/.local/share}/pnpm/store/v11"
fi
mkdir -p "${store}"
echo "ensure-pnpm-store: ready ${store}"
