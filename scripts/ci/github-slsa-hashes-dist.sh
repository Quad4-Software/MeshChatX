#!/usr/bin/env bash
# Emit base64-encoded sha256sum lines for files in ./dist (SLSA generic generator input).
# Excludes *.cosign.bundle. Writes "hashes=<base64>" to GITHUB_OUTPUT when set.
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


cd "$(dirname "$0")/../.."
if [ ! -d dist ]; then
    echo "dist/ missing" >&2
    exit 1
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

(
    cd dist
    find . -maxdepth 1 -type f ! -name '*.cosign.bundle' -printf '%P\0' | sort -z | xargs -0 sha256sum
) >"$tmp"

if [ ! -s "$tmp" ]; then
    echo "No files to hash under dist/" >&2
    exit 1
fi

b64="$(base64 -w0 <"$tmp")"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "hashes=${b64}" >>"$GITHUB_OUTPUT"
else
    printf '%s\n' "$b64"
fi
