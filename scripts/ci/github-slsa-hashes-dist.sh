#!/usr/bin/env bash
# Emit base64-encoded sha256sum lines for files in ./dist (SLSA generic generator input).
# Excludes *.cosign.bundle. Writes "hashes=<base64>" to GITHUB_OUTPUT when set.
set -euo pipefail

# Self-hosted runners may lack /tmp; mktemp honours TMPDIR.
if [ ! -d /tmp ] || [ ! -w /tmp ]; then
    _ci_tmp="${RUNNER_TEMP:-${HOME}/.meshchatx-ci}/tmp"
    mkdir -p "${_ci_tmp}" 2>/dev/null && {
        TMPDIR="${_ci_tmp}"
        export TMPDIR
        [ -n "${GITHUB_ENV:-}" ] && echo "TMPDIR=${TMPDIR}" >> "${GITHUB_ENV}"
    }
fi
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
