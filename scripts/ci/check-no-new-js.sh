#!/bin/sh
# Ratchet: refuse new JavaScript files under the Svelte/TS frontend tree.
# Existing .js files stay; new code under meshchatx/src/frontend must be .ts.
# Usage: check-no-new-js.sh <base-ref>   (base must be fetched already)
set -eu

base="${1:?usage: check-no-new-js.sh <base-ref>}"

new_js=$(git diff --diff-filter=A --name-only "${base}...HEAD" -- \
    "meshchatx/src/frontend/**/*.js" "meshchatx/src/frontend/*.js")

if [ -n "${new_js}" ]; then
    echo "error: new .js files under meshchatx/src/frontend are not allowed" >&2
    echo "the frontend is migrating to TypeScript; write new code as .ts/.svelte" >&2
    printf '%s\n' "${new_js}" >&2
    exit 1
fi
