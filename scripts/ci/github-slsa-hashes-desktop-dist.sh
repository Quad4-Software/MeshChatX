#!/usr/bin/env bash
# Emit base64-encoded sha256sum lines for Electron outputs under downloaded artifact roots.
# Subject paths are the relative paths passed to sha256sum (stable for slsa-verifier).
set -euo pipefail

# /tmp can disappear mid-run on self-hosted runners (tmpfiles cleanup,
# unmounted tmpfs), so never depend on it: mktemp and friends honour
# TMPDIR. Always point TMPDIR at a user-writable per-job dir and
# propagate it to later steps via GITHUB_ENV.
_ci_tmp=""
for _ci_cand in "${RUNNER_TEMP:-}" "${HOME:-}" "${GITHUB_WORKSPACE:-}"; do
    [ -n "${_ci_cand}" ] || continue
    _ci_cand="${_ci_cand}/.meshchatx-ci-tmp"
    if mkdir -p "${_ci_cand}" 2>/dev/null && [ -w "${_ci_cand}" ]; then
        _ci_tmp="${_ci_cand}"
        break
    fi
done
if [ -n "${_ci_tmp}" ]; then
    TMPDIR="${_ci_tmp}"
    export TMPDIR
    [ -n "${GITHUB_ENV:-}" ] && echo "TMPDIR=${TMPDIR}" >> "${GITHUB_ENV}"
    echo "ci: TMPDIR=${TMPDIR}"
else
    echo "ci: WARNING: no writable temp dir available" >&2
fi
unset _ci_cand
unset _ci_tmp


if [ "$#" -lt 1 ]; then
    echo "usage: $0 <root> [root...]" >&2
    exit 1
fi

roots=()
for d in "$@"; do
    [ -d "$d" ] && roots+=("$d")
done
if [ "${#roots[@]}" -eq 0 ]; then
    echo "No existing directories in: $* (emitting empty hashes)" >&2
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        echo "hashes=" >>"$GITHUB_OUTPUT"
    else
        printf '%s\n' ""
    fi
    exit 0
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

find "${roots[@]}" -type f \( \
    -name '*.exe' -o -name '*.dmg' -o -name '*.blockmap' -o \
    \( -name '*.yml' ! -name '*.so.yml' \) -o \
    \( -name '*.yaml' ! -name '*.so.yaml' \) \
    \) ! -name 'library.zip' ! -path '*/.*' -print0 \
    | LC_ALL=C sort -z \
    | xargs -0r sha256sum >"$tmp"

if [ ! -s "$tmp" ]; then
    echo "No matching dist files under: ${roots[*]} (emitting empty hashes)" >&2
    b64=""
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        echo "hashes=${b64}" >>"$GITHUB_OUTPUT"
    else
        printf '%s\n' "$b64"
    fi
    exit 0
fi

b64="$(base64 -w0 <"$tmp")"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "hashes=${b64}" >>"$GITHUB_OUTPUT"
else
    printf '%s\n' "$b64"
fi
